using System;
using System.Windows.Forms;
using Microsoft.Win32;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Liga/desliga a inicialização junto com o Windows (HKCU\...\Run).
    /// Não precisa de administrador.
    /// </summary>
    internal static class AutoStartManager
    {
        private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
        private const string ValueName = "BillFluxPrintAgent";

        public static bool IsEnabled()
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(RunKey, false))
                {
                    if (key == null) return false;
                    return key.GetValue(ValueName) != null;
                }
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível ler a inicialização automática", ex);
                return false;
            }
        }

        public static void SetEnabled(bool enabled)
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(RunKey, true))
                {
                    if (key == null) return;
                    if (enabled)
                    {
                        key.SetValue(ValueName, "\"" + Application.ExecutablePath + "\"");
                    }
                    else
                    {
                        key.DeleteValue(ValueName, false);
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível alterar a inicialização automática", ex);
            }
        }
    }
}
