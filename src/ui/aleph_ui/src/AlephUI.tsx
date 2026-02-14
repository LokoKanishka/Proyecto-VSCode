/**
 * AlephUI Component - Interfaz Cyberpunk-Gótica para LUCY ALEPH.
 * Versión 3.0: Command Deck Simétrico (2:8:2)
 * Requisitos: tailwindcss, lucide-react, framer-motion, socket.io-client.
 */
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, Terminal, ShieldAlert, Activity } from 'lucide-react';
import { io, Socket } from 'socket.io-client';

const AlephUI: React.FC = () => {
    const [status, setStatus] = useState<any>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [command, setCommand] = useState("");
    const [connected, setConnected] = useState(false);

    // Socket ref
    const socketRef = useRef<Socket | null>(null);

    useEffect(() => {
        // Conexión al API Gateway (Puerto 5052)
        const socket = io('http://localhost:5052', {
            transports: ['websocket', 'polling']
        });
        socketRef.current = socket;

        socket.on('connect', () => {
            setConnected(true);
            setLogs(prev => [`[SYSTEM] Uplink established with Neural Core.`, ...prev]);
        });

        socket.on('disconnect', () => {
            setConnected(false);
            setLogs(prev => [`[SYSTEM] Uplink lost. Reconnecting...`, ...prev]);
        });

        // Escuchar eventos del enjambre
        socket.on('lucy_event', (event: any) => {
            if (event.content === "TELEMETRY_UPDATE") {
                // Actualizar estado de hardware
                if (event.data && event.data.gpu) {
                    setStatus({
                        vram_used: event.data.gpu.vram_used,
                        vram_total: event.data.gpu.vram_total,
                        gpu_load: event.data.gpu.utilization,
                        temp: event.data.gpu.temp,
                        sovereignty: event.data.sovereignty
                    });
                }
            } else {
                // Logs genéricos o pensamientos
                const timestamp = new Date(event.timestamp * 1000).toLocaleTimeString();
                const sender = event.sender.toUpperCase();
                const content = event.content;
                setLogs(prev => [`[${timestamp}] ${sender}: ${content}`, ...prev].slice(0, 50));
            }
        });

        return () => {
            socket.disconnect();
        };
    }, []);

    const handleCommand = (e: React.FormEvent) => {
        e.preventDefault();
        if (!command.trim()) return;

        // Enviar comando al backend
        socketRef.current?.emit('lucy_command', {
            content: command,
            receiver: "manager" // Default receiver
        });

        setLogs(prev => [`[${new Date().toLocaleTimeString()}] USER_CMD: ${command}`, ...prev]);
        setCommand("");
    }

    return (
        <div className="min-h-screen bg-[#020203] text-[#00fafe] font-mono p-10 selection:bg-[#b366ff] selection:text-white overflow-hidden flex flex-col items-center">
            {/* Fondo Cinemático Blackwell */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00fafe]/40 to-transparent" />
                <div className="absolute top-[-15%] left-[10%] w-[600px] h-[600px] bg-[#b366ff]/5 rounded-full blur-[160px]" />
                <div className="absolute bottom-[-10%] right-[10%] w-[500px] h-[500px] bg-[#00fafe]/5 rounded-full blur-[140px]" />
            </div>

            {/* Contenedor Principal Limitado (Soberano) */}
            <div className="relative z-10 w-full max-w-[1700px] h-full flex flex-col flex-1">

                {/* Header Simétrico */}
                <header className="flex justify-between items-center border-b-2 border-[#00fafe]/10 pb-8 mb-10 w-full">
                    <div className="flex-1">
                        <div className="flex items-center gap-4 text-xs opacity-40 uppercase tracking-[0.4em] mb-2 font-black">
                            <Activity size={12} /> Sync_Protocol: Active
                        </div>
                        <h1 className="text-6xl font-black tracking-tighter uppercase italic text-transparent bg-clip-text bg-gradient-to-b from-white via-[#00fafe] to-[#b366ff]">
                            Lucy Aleph
                        </h1>
                    </div>

                    <div className="flex gap-10 items-center bg-black/40 px-8 py-4 border border-white/5 backdrop-blur-md rounded-sm">
                        <div className="flex flex-col items-center">
                            <span className="text-[10px] opacity-40 uppercase tracking-widest mb-1">Uplink</span>
                            <div className={`h-2 w-12 rounded-full ${connected ? "bg-green-400 shadow-[0_0_10px_green]" : "bg-red-600 shadow-[0_0_10px_red] animate-pulse"}`} />
                            <span className="text-[9px] mt-1 font-bold">{connected ? "STABLE" : "OFFLINE"}</span>
                        </div>
                        <div className="h-10 w-[1px] bg-white/10" />
                        <div className="text-right">
                            <span className="text-[10px] opacity-40 uppercase tracking-widest block mb-1">Cortex State</span>
                            <span className="text-xl font-black tracking-widest text-white">SOVEREIGN</span>
                        </div>
                    </div>
                </header>

                {/* Grid Deck Simétrico: 2-8-2 */}
                <main className="grid grid-cols-12 gap-10 flex-1 min-h-0 mb-10">

                    {/* Panel Izquierdo: Métricas (col 3) */}
                    <aside className="col-span-3 flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2">
                        <div className="p-8 bg-black/50 border-l-4 border-[#00fafe] backdrop-blur-xl">
                            <h2 className="text-sm font-black uppercase tracking-[0.3em] mb-8 text-[#00fafe] flex items-center gap-2">
                                <Cpu size={16} /> Hardware Core
                            </h2>

                            <TelemetryMetric
                                label="Blackwell VRAM"
                                value={status ? (status.vram_used / (status.vram_total || 1)) * 100 : 0}
                                detail={status ? `${status.vram_used}MB` : "N/A"}
                                color="bg-[#00fafe]"
                            />

                            <TelemetryMetric
                                label="Neural Load"
                                value={status?.gpu_load || 0}
                                detail={`${status?.gpu_load || 0}%`}
                                color="bg-[#b366ff]"
                            />

                            <div className="mt-8 pt-6 border-t border-white/5 space-y-4 text-xs font-bold uppercase italic opacity-60">
                                <div className="flex justify-between">
                                    <span>Core Temp</span>
                                    <span className="text-[#00fafe]">{status?.temp || 0}°C</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Sync Latency</span>
                                    <span>0.4ms</span>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 bg-[#b366ff]/5 border border-[#b366ff]/20 rounded-sm">
                            <div className="flex items-center gap-4 text-[#b366ff] animate-pulse">
                                <ShieldAlert size={20} />
                                <span className="text-[10px] font-black uppercase tracking-[0.2em]">Neural Watchdog Active</span>
                            </div>
                        </div>
                    </aside>

                    {/* Panel Central: Stream (col 6) */}
                    <section className="col-span-6 flex flex-col bg-black/60 border border-white/5 backdrop-blur-3xl overflow-hidden relative shadow-[0_0_100px_rgba(0,0,0,0.5)]">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#b366ff]/50 to-transparent" />

                        <div className="p-8 flex-1 overflow-y-auto custom-scrollbar flex flex-col-reverse">
                            <AnimatePresence initial={false}>
                                {logs.length === 0 ? (
                                    <div className="h-full flex items-center justify-center italic opacity-10 text-xl tracking-[0.5em] uppercase text-center p-20">
                                        Escuchando latidos del enjambre...
                                    </div>
                                ) : (
                                    logs.map((log, i) => (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="mb-4 py-2 border-l border-white/10 pl-6 hover:bg-white/5 transition-all group"
                                        >
                                            <div className="text-[9px] uppercase opacity-30 group-hover:opacity-100 transition-opacity mb-1 tracking-widest">
                                                Sequence_Log_00{i} // 2026.02.13
                                            </div>
                                            <p className="text-base text-white/90 leading-tight">
                                                <span className="text-[#00fafe] mr-3">#</span> {log}
                                            </p>
                                        </motion.div>
                                    ))
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Tactical Command Input */}
                        <div className="p-8 bg-black/80 border-t border-white/10">
                            <form onSubmit={handleCommand} className="relative group">
                                <div className={`absolute -inset-0.5 bg-gradient-to-r from-[#00fafe] to-[#b366ff] rounded-none blur opacity-0 group-focus-within:opacity-25 transition duration-500 ${!connected ? "invisible" : ""}`} />
                                <input
                                    type="text"
                                    value={command}
                                    onChange={(e) => setCommand(e.target.value)}
                                    className={`w-full bg-[#050505] border-2 ${connected ? "border-[#00fafe]/40" : "border-red-900/40 text-red-500"} p-5 text-xl font-bold focus:outline-none focus:border-[#00fafe] transition-all tracking-wider placeholder:opacity-10 text-white`}
                                    placeholder={connected ? "INTRODUZCA COMANDO DIRECTO..." : "SISTEMA BLOQUEADO // RECONECTE CORE"}
                                    disabled={!connected}
                                />
                                <div className="absolute right-6 top-1/2 -translate-y-1/2 flex items-center gap-4 pointer-events-none opacity-40">
                                    <span className="text-[10px] font-black uppercase tracking-widest hidden lg:block">Exec_Buffer_Sovereign</span>
                                    <Terminal size={18} />
                                </div>
                            </form>
                        </div>
                    </section>

                    {/* Panel Derecho: System Info (col 3) */}
                    <aside className="col-span-3 flex flex-col gap-6">
                        <div className="p-8 bg-black/50 border-r-4 border-[#b366ff] text-right backdrop-blur-xl">
                            <h2 className="text-sm font-black uppercase tracking-[0.3em] mb-8 text-[#b366ff] flex items-center justify-end gap-2">
                                System State <Activity size={16} />
                            </h2>

                            <div className="space-y-6">
                                <div className="flex flex-col items-end">
                                    <span className="text-[10px] opacity-40 uppercase tracking-widest mb-1">Consciousness Phase</span>
                                    <span className="text-lg font-bold tracking-tighter">ALPHA_SINGULARITY</span>
                                </div>
                                <div className="flex flex-col items-end">
                                    <span className="text-[10px] opacity-40 uppercase tracking-widest mb-1">Active Workers</span>
                                    <span className="text-lg font-bold text-[#b366ff]">07 / 09</span>
                                </div>
                                <div className="flex flex-col items-end border-t border-white/5 pt-6">
                                    <span className="text-[10px] opacity-40 uppercase tracking-widest mb-2">Memory Hash</span>
                                    <div className="text-[9px] font-mono break-all leading-tight opacity-50 bg-black/40 p-3 italic">
                                        {(status?.sovereignty || "Awaiting_Synaptic_Connection_0x82...").substring(0, 80)}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex-1 bg-gradient-to-b from-transparent to-[#00fafe]/5 border border-white/5 flex items-center justify-center p-8 text-center group">
                            <div>
                                <div className="w-16 h-16 border-2 border-[#b366ff]/20 rounded-full mx-auto mb-4 flex items-center justify-center group-hover:border-[#b366ff]/60 transition-colors duration-700 animate-pulse">
                                    <div className="w-8 h-8 bg-[#b366ff]/30 rounded-full blur-lg" />
                                </div>
                                <span className="text-[10px] uppercase tracking-[0.4em] opacity-40">Synaptic Heartbeat</span>
                            </div>
                        </div>
                    </aside>

                </main>

                <footer className="flex justify-between items-center text-[10px] opacity-20 font-black uppercase tracking-[0.6em] py-4 border-t border-white/5 w-full">
                    <span>Aleph Command Deck v3.0</span>
                    <span className="hidden md:block">Distributed Intelligence Architecture</span>
                    <span>2026 // Lucy Core</span>
                </footer>
            </div>
        </div>
    );
};

const TelemetryMetric = ({ label, value, detail, color }: any) => (
    <div className="mb-8 last:mb-0">
        <div className="flex justify-between items-end mb-3 text-[10px] uppercase tracking-tighter">
            <span className="opacity-60 italic">{label}</span>
            <span className="font-black text-[#00fafe]">{detail}</span>
        </div>
        <div className="h-[4px] w-full bg-white/5 overflow-hidden">
            <motion.div
                className={`h-full ${color} shadow-[0_0_10px_currentColor]`}
                initial={{ width: 0 }}
                animate={{ width: `${value}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
            />
        </div>
    </div>
);

export default AlephUI;
