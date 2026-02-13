/**
 * AlephUI Component - Interfaz Cyberpunk-Gótica para LUCY ALEPH.
 * Requisitos: tailwindcss, lucide-react, framer-motion.
 */
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, Terminal, ShieldAlert } from 'lucide-react';

const AlephUI: React.FC = () => {
    const [status, setStatus] = useState<any>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [command, setCommand] = useState("");

    // Simulación de WebSocket para monitorización de hardware
    useEffect(() => {
        const interval = setInterval(() => {
            // En producción, estos datos provienen de AlephNucleus.get_hardware_telemetry
            setStatus({
                vram_used: 12400 + Math.random() * 500,
                vram_total: 32768,
                gpu_load: 45 + Math.random() * 10,
                temp: 62,
                power: 320
            });

            // Simular logs
            if (Math.random() > 0.8) {
                const newLog = `[${new Date().toLocaleTimeString()}] THOUGHT_ACTOR: Analyzing context vector...`;
                setLogs(prev => [newLog, ...prev].slice(0, 50));
            }
        }, 1500);
        return () => clearInterval(interval);
    }, []);

    const handleCommand = (e: React.FormEvent) => {
        e.preventDefault();
        if (!command.trim()) return;
        setLogs(prev => [`[${new Date().toLocaleTimeString()}] USER_CMD: ${command}`, ...prev]);
        setCommand("");
    }

    return (
        <div className="min-h-screen bg-[#020203] text-[#00fafe] font-mono p-6 selection:bg-[#b366ff] selection:text-white overflow-hidden">
            {/* Efectos de fondo: Orbes de luz gótica */}
            <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden">
                <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-[#b366ff]/5 rounded-full blur-[140px]" />
                <div className="absolute bottom-[-5%] left-[-5%] w-[400px] h-[400px] bg-[#00fafe]/5 rounded-full blur-[120px]" />
            </div>

            <header className="relative z-10 flex justify-between items-end border-b border-[#00fafe]/20 pb-4 mb-8">
                <div>
                    <h1 className="text-4xl font-black tracking-[0.2em] uppercase italic text-transparent bg-clip-text bg-gradient-to-r from-[#00fafe] to-[#b366ff]">
                        Lucy Aleph UI
                    </h1>
                    <p className="text-[10px] uppercase opacity-50 mt-1">Sovereign Intelligence Command Interface v2.0</p>
                </div>
                <div className="flex gap-6 text-right">
                    <div className="flex flex-col">
                        <span className="text-[10px] opacity-50 italic">S_LUCY INDEX</span>
                        <span className="text-lg font-bold text-green-400">1.0</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] opacity-50 italic">NUCLEUS STATE</span>
                        <span className="text-lg font-bold">SOVEREIGN</span>
                    </div>
                </div>
            </header>

            <main className="relative z-10 grid grid-cols-12 gap-6">
                {/* Panel de Telemetría GPU: RTX 5090 Monitor */}
                <section className="col-span-4 space-y-6">
                    <div className="p-6 rounded-sm bg-black/40 backdrop-blur-md border border-[#00fafe]/10 shadow-[0_0_30px_rgba(0,0,0,0.5)]">
                        <h2 className="flex items-center gap-2 mb-6 text-xs font-bold uppercase tracking-widest text-[#b366ff]">
                            <Cpu size={14} /> Telemetría Blackwell
                        </h2>

                        <TelemetryMetric
                            label="VRAM Usage"
                            value={status ? (status.vram_used / status.vram_total) * 100 : 0}
                            detail={`${status?.vram_used.toFixed(0)} / 32GB`}
                            color="bg-[#00fafe]"
                        />

                        <TelemetryMetric
                            label="GPU Compute"
                            value={status?.gpu_load || 0}
                            detail={`${status?.gpu_load.toFixed(1)}%`}
                            color="bg-[#b366ff]"
                        />

                        <div className="mt-6 pt-6 border-t border-white/5 grid grid-cols-2 gap-4 text-[10px]">
                            <div className="flex flex-col">
                                <span className="opacity-40 italic">CORE TEMP</span>
                                <span className="text-sm">{status?.temp}°C</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="opacity-40 italic">POWER DRAW</span>
                                <span className="text-sm">{status?.power}W</span>
                            </div>
                        </div>
                    </div>

                    <div className="p-4 rounded-sm bg-[#b366ff]/5 border border-[#b366ff]/20">
                        <div className="flex items-center gap-3 text-[#b366ff]">
                            <ShieldAlert size={18} />
                            <span className="text-[10px] font-bold uppercase tracking-tighter">
                                Neural Watchdog: Vigilancia Activa
                            </span>
                        </div>
                    </div>
                </section>

                {/* Consola de Comandos y Pensamiento */}
                <section className="col-span-8 flex flex-col h-[70vh]">
                    <div className="flex-1 p-6 bg-black/60 backdrop-blur-xl border border-[#00fafe]/20 rounded-sm shadow-inner overflow-hidden flex flex-col">
                        <h2 className="flex items-center gap-2 mb-4 text-xs font-bold uppercase tracking-widest opacity-70 italic">
                            <Terminal size={14} /> Stream de Consciencia
                        </h2>

                        <div className="flex-1 overflow-y-auto space-y-3 pr-4 custom-scrollbar">
                            <AnimatePresence>
                                {logs.map((log, i) => (
                                    <motion.div
                                        key={i}
                                        initial={{ opacity: 0, x: -5 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0 }}
                                        className="text-sm leading-relaxed border-l-2 border-[#b366ff]/30 pl-3"
                                    >
                                        <span className="text-[#FCEE0A] opacity-80 mr-2 text-[10px] font-bold">
                                            {">"}
                                        </span>
                                        {log}
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>

                        <div className="mt-6 relative">
                            <form onSubmit={handleCommand}>
                                <input
                                    type="text"
                                    value={command}
                                    onChange={(e) => setCommand(e.target.value)}
                                    className="w-full bg-black/80 border border-[#00fafe]/30 rounded-none p-4 text-sm focus:outline-none focus:border-[#00fafe] transition-colors placeholder:text-[#00fafe]/20 italic"
                                    placeholder="Escriba comando para el enjambre Aleph..."
                                />
                            </form>
                            <div className="absolute right-4 top-1/2 -translate-y-1/2 flex gap-2">
                                <span className="text-[10px] opacity-30">ENTER TO EXEC</span>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer className="fixed bottom-4 left-6 text-[9px] uppercase tracking-[0.3em] opacity-30">
                Aleph Nucleus Core | Distributed Architecture | No Rights Reserved
            </footer>
        </div>
    );
};

const TelemetryMetric = ({ label, value, detail, color }: any) => (
    <div className="mb-6 last:mb-0">
        <div className="flex justify-between items-end mb-2 text-[10px] uppercase tracking-tighter">
            <span className="opacity-60 italic">{label}</span>
            <span className="font-bold">{detail}</span>
        </div>
        <div className="h-[2px] w-full bg-white/5 overflow-hidden">
            <motion.div
                className={`h-full ${color}`}
                initial={{ width: 0 }}
                animate={{ width: `${value}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
            />
        </div>
    </div>
);

export default AlephUI;
