using System;
using System.IO;
using System.Text;

namespace BillFlux.PrintAgent
{
    /// <summary>Log simples em %APPDATA%\BillFlux\print-agent.log.</summary>
    internal static class Log
    {
        private static readonly object Sync = new object();

        public static string DataFolder
        {
            get
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    "BillFlux"
                );
            }
        }

        public static string LogPath
        {
            get { return Path.Combine(DataFolder, "print-agent.log"); }
        }

        public static void Info(string message)
        {
            Write("INFO", message);
        }

        public static void Error(string message, Exception ex)
        {
            Write("ERRO", message + (ex == null ? string.Empty : ": " + ex));
        }

        private static void Write(string level, string message)
        {
            try
            {
                lock (Sync)
                {
                    Directory.CreateDirectory(DataFolder);
                    var line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " [" + level + "] " + message;
                    File.AppendAllText(LogPath, line + Environment.NewLine, Encoding.UTF8);
                    Trim();
                }
            }
            catch
            {
                // Log nunca derruba o agente.
            }
        }

        /// <summary>Mantém o arquivo pequeno (máximo ~1 MB).</summary>
        private static void Trim()
        {
            var info = new FileInfo(LogPath);
            if (!info.Exists || info.Length < 1024 * 1024) return;

            var lines = File.ReadAllLines(LogPath);
            var start = Math.Max(0, lines.Length - 2000);
            var kept = new string[lines.Length - start];
            Array.Copy(lines, start, kept, 0, kept.Length);
            File.WriteAllLines(LogPath, kept, Encoding.UTF8);
        }
    }
}
