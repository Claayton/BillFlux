using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Configuração em %APPDATA%\BillFlux\print-agent.json.
    /// Só guarda escolhas locais do caixa (impressora, papel, auto-start).
    /// </summary>
    public sealed class AgentConfig
    {
        public string Printer { get; set; }
        public int WidthMm { get; set; }
        public bool AutoStart { get; set; }
        public int Port { get; set; }

        public AgentConfig()
        {
            Printer = string.Empty;
            WidthMm = 80;
            AutoStart = false;
            Port = 9911;
        }

        public static string Folder
        {
            get { return Log.DataFolder; }
        }

        public static string FilePath
        {
            get { return Path.Combine(Folder, "print-agent.json"); }
        }

        public static string Version
        {
            get
            {
                var version = Assembly.GetExecutingAssembly().GetName().Version;
                return version == null ? "1.0.0" : version.ToString(3);
            }
        }

        public static AgentConfig Load()
        {
            try
            {
                if (File.Exists(FilePath))
                {
                    var json = File.ReadAllText(FilePath, Encoding.UTF8);
                    var serializer = new JavaScriptSerializer();
                    var config = serializer.Deserialize<AgentConfig>(json);
                    if (config != null)
                    {
                        config.Normalize();
                        return config;
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível ler a configuração; usando os padrões", ex);
            }

            return new AgentConfig();
        }

        public void Save()
        {
            Normalize();
            try
            {
                Directory.CreateDirectory(Folder);
                var serializer = new JavaScriptSerializer();
                var json = serializer.Serialize(this);
                File.WriteAllText(FilePath, json, Encoding.UTF8);
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível salvar a configuração", ex);
            }
        }

        public void Normalize()
        {
            if (WidthMm != 58 && WidthMm != 80) WidthMm = 80;
            if (Port < 1024 || Port > 65535) Port = 9911;
            if (Printer == null) Printer = string.Empty;
        }

        public Dictionary<string, object> ToStatus()
        {
            return new Dictionary<string, object>
            {
                { "printer", Printer },
                { "widthMm", WidthMm },
                { "autoStart", AutoStart },
                { "port", Port },
            };
        }
    }
}
