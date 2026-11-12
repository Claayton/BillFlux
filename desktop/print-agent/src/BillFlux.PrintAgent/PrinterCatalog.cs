using System;
using System.Collections.Generic;
using System.Drawing.Printing;
using System.Linq;

namespace BillFlux.PrintAgent
{
    /// <summary>Impressoras instaladas no Windows.</summary>
    internal static class PrinterCatalog
    {
        public static string[] Names()
        {
            try
            {
                return PrinterSettings.InstalledPrinters
                    .Cast<string>()
                    .Where(name => !string.IsNullOrWhiteSpace(name))
                    .OrderBy(name => name, StringComparer.CurrentCultureIgnoreCase)
                    .ToArray();
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível listar as impressoras", ex);
                return new string[0];
            }
        }

        public static bool Exists(string name)
        {
            if (string.IsNullOrWhiteSpace(name)) return false;
            return Names().Any(
                installed => string.Equals(installed, name.Trim(), StringComparison.OrdinalIgnoreCase)
            );
        }
    }
}
