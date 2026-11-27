#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

#define CAP 32767

static wchar_t root[CAP], python[CAP], script[CAP], command[CAP], env_value[CAP];
static size_t used;

static int report(const wchar_t *message, DWORD error)
{
    wchar_t detail[512], text[1024];
    if (error && FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                                NULL, error, 0, detail, 512, NULL)) {
        swprintf(text, sizeof text / sizeof *text, L"%ls\n\n%ls", message, detail);
        MessageBoxW(NULL, text, L"amdl Masaüstü", MB_OK | MB_ICONERROR);
    } else
        MessageBoxW(NULL, message, L"amdl Masaüstü", MB_OK | MB_ICONERROR);
    return 1;
}

static BOOL bundle_path(wchar_t *out, const wchar_t *suffix)
{
    if (wcslen(root) + wcslen(suffix) >= CAP) {
        SetLastError(ERROR_FILENAME_EXCED_RANGE);
        return FALSE;
    }
    wcscpy(out, root);
    wcscat(out, suffix);
    return TRUE;
}

static BOOL set_bundle_env(const wchar_t *key, const wchar_t *suffix)
{
    return bundle_path(env_value, suffix) && SetEnvironmentVariableW(key, env_value);
}

static BOOL setup_environment(void)
{
    if (!set_bundle_env(L"GI_TYPELIB_PATH", L"runtime\\lib\\girepository-1.0") ||
        !set_bundle_env(L"GSETTINGS_SCHEMA_DIR", L"runtime\\share\\glib-2.0\\schemas") ||
        !set_bundle_env(L"GDK_PIXBUF_MODULE_FILE", L"runtime\\lib\\gdk-pixbuf-2.0\\2.10.0\\loaders.cache") ||
        !set_bundle_env(L"XDG_DATA_DIRS", L"runtime\\share") ||
        !bundle_path(env_value, L"runtime\\bin;"))
        return FALSE;

    /* Alt sureclerde de once paketlenmis DLL ve araclar aransin. */
    DWORD start = (DWORD)wcslen(env_value);
    SetLastError(ERROR_SUCCESS);
    DWORD got = GetEnvironmentVariableW(L"PATH", env_value + start, CAP - start);
    if (got >= CAP - start) {
        SetLastError(ERROR_INSUFFICIENT_BUFFER);
        return FALSE;
    }
    if (got == 0) {
        DWORD error = GetLastError();
        if (error != ERROR_SUCCESS && error != ERROR_ENVVAR_NOT_FOUND)
            return FALSE;
        env_value[start - 1] = L'\0';
    }
    return SetEnvironmentVariableW(L"PATH", env_value);
}

static BOOL append(wchar_t ch)
{
    if (used >= CAP - 1)
        return FALSE;
    command[used++] = ch;
    return TRUE;
}

/* CRT kurali: tirnak onundeki ters egik cizgileri ikiye katla;
   kapanis tirnagindan onceki diziyi de kacir. */
static BOOL append_arg(const wchar_t *arg)
{
    if ((used && !append(L' ')) || !append(L'"'))
        return FALSE;
    for (;;) {
        size_t slashes = 0;
        while (*arg == L'\\') {
            ++slashes;
            ++arg;
        }
        if (*arg == L'"' || *arg == L'\0')
            slashes *= 2;
        for (size_t i = 0; i < slashes; ++i)
            if (!append(L'\\'))
                return FALSE;
        if (*arg == L'\0')
            return append(L'"');
        if ((*arg == L'"' && !append(L'\\')) || !append(*arg++))
            return FALSE;
    }
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR line, int show)
{
    (void)instance;
    (void)previous;
    (void)line;
    (void)show;
    DWORD length = GetModuleFileNameW(NULL, root, CAP);
    if (length == 0 || length >= CAP)
        return report(L"AMDL konumu okunamadi", GetLastError());
    wchar_t *slash = wcsrchr(root, L'\\');
    if (!slash)
        return report(L"AMDL konumu gecersiz", 0);
    slash[1] = L'\0';

    if (!bundle_path(python, L"runtime\\bin\\pythonw.exe") ||
        !bundle_path(script, L"app\\portable.py") || !setup_environment())
        return report(L"AMDL calisma ortami hazirlanamadi", GetLastError());
    DWORD attr = GetFileAttributesW(script);
    if (attr == INVALID_FILE_ATTRIBUTES || (attr & FILE_ATTRIBUTE_DIRECTORY))
        return report(L"app\\portable.py eksik. Arşivi tamamen çıkar ve klasörü birlikte tut.\n"
                      L"Extract the entire archive and keep the folder together.", 0);
    attr = GetFileAttributesW(python);
    if (attr == INVALID_FILE_ATTRIBUTES || (attr & FILE_ATTRIBUTE_DIRECTORY))
        return report(L"runtime\\bin\\pythonw.exe eksik. Güncelleme ZIP’i tek başına çalışmaz.\n"
                      L"The update ZIP requires an existing full portable bundle.", 0);

    int argc;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv)
        return report(L"AMDL komut satiri okunamadi", GetLastError());
    BOOL fits = append_arg(python) && append_arg(L"-Es") && append_arg(script);
    for (int i = 1; fits && i < argc; ++i)
        fits = append_arg(argv[i]);
    LocalFree(argv);
    if (!fits)
        return report(L"AMDL komut satiri cok uzun", 0);
    command[used] = L'\0';

    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION child;
    startup.cb = sizeof(startup);
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, 0, NULL, root, &startup, &child))
        return report(L"AMDL baslatilamadi (runtime\\bin\\pythonw.exe)", GetLastError());
    CloseHandle(child.hThread);

    /* Otomatik denemeler ve cagiran surecler Python'un cikis kodunu alir. */
    DWORD result;
    if (WaitForSingleObject(child.hProcess, INFINITE) != WAIT_OBJECT_0 ||
        !GetExitCodeProcess(child.hProcess, &result)) {
        DWORD error = GetLastError();
        CloseHandle(child.hProcess);
        return report(L"AMDL sureci izlenemedi", error);
    }
    CloseHandle(child.hProcess);
    return (int)result;
}
