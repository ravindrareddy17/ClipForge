import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, FolderKanban, Radio, Video, Cpu, Film, 
  Share2, Calendar, BarChart3, Palette, Sliders, Edit3, 
  RefreshCw, Upload, CheckCircle2, Clock, 
  Scissors, Settings, Sparkles, Plus, Check, ChevronRight
} from 'lucide-react';

// API Configuration
const API_URL = "http://localhost:8000";

// --- Types ---
interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

interface VideoFile {
  id: string;
  project_id: string;
  filename: string;
  file_path: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  status: string; // 'pending', 'processing', 'completed', 'failed'
  transcript?: any;
  scenes?: any;
  created_at: string;
}

interface Clip {
  id: string;
  video_id: string;
  title: string;
  start_time: number;
  end_time: number;
  duration: number;
  score: number;
  explanation: string;
  status: string; // 'rendering', 'completed', 'failed', 'ready_to_render'
  file_path?: string;
  subtitles: any[];
  subtitle_style: any;
  created_at: string;
}

export default function App() {
  // Sidebar State
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  
  // App States
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
  
  // Form states
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [localVideoPath, setLocalVideoPath] = useState("");
  
  // System states
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  // Editor States
  const [clipTitle, setClipTitle] = useState("");
  const [clipStart, setClipStart] = useState(0);
  const [clipEnd, setClipEnd] = useState(0);
  const [clipSubtitles, setClipSubtitles] = useState<any[]>([]);
  const [subtitleStyle, setSubtitleStyle] = useState<any>({
    font_family: "Montserrat",
    font_size: 28,
    primary_color: "#FFFFFF",
    accent_color: "#FF0055",
    outline_color: "#000000",
    margin_v: 140
  });
  
  // Simulated Scheduler items
  const scheduledClips = [
    { id: "1", title: "React Hooks explained", time: "14:30", platform: "YouTube", date: "2026-07-16" },
    { id: "2", title: "Face tracking demo", time: "18:00", platform: "TikTok", date: "2026-07-16" },
    { id: "3", title: "Why Ollama is fast", time: "10:00", platform: "Instagram", date: "2026-07-17" },
  ];

  // Brand presest state
  const [brandPreset, setBrandPreset] = useState({
    logo: "",
    watermark: "ClipForge AI",
    outro: "",
    brand_colors: ["#FF0055", "#00F0FF", "#000000"],
    font_family: "Montserrat"
  });

  // Automation flowchart active state
  const [automationNodes, setAutomationNodes] = useState([
    { id: "import", label: "Video Imported", active: true },
    { id: "scene", label: "Scene Detection", active: true },
    { id: "moment", label: "AI Moments", active: true },
    { id: "subtitles", label: "Generate Subtitles", active: true },
    { id: "crop", label: "Face Track Crop", active: true },
    { id: "render", label: "Auto Render", active: false },
    { id: "schedule", label: "Schedule Post", active: false }
  ]);

  // Check Backend Status
  const checkBackendStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/projects`);
      if (res.status === 200) {
        setIsBackendOnline(true);
        // Load initial data
        const projData = await res.json();
        setProjects(projData);
        if (projData.length > 0 && !currentProject) {
          setCurrentProject(projData[0]);
        }
      }
    } catch (e) {
      setIsBackendOnline(false);
    }
  };

  useEffect(() => {
    checkBackendStatus();
    console.log("Scheduler loaded with", scheduledClips.length, "items.");
    const interval = setInterval(checkBackendStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch videos when current project changes
  useEffect(() => {
    if (currentProject && isBackendOnline) {
      fetchVideos();
    } else if (!isBackendOnline) {
      // Mock Projects & Videos for Demo Mode
      const mockProjects = [
        { id: "demo-p1", name: "Mr Creator", description: "Main channel shorts content", created_at: new Date().toISOString() }
      ];
      setProjects(mockProjects);
      setCurrentProject(mockProjects[0]);
      
      const mockVideos = [
        { id: "demo-v1", project_id: "demo-p1", filename: "podcast_episode_42.mp4", file_path: "C:\\videos\\podcast_42.mp4", duration: 180, width: 1920, height: 1080, fps: 30, status: "completed", created_at: new Date().toISOString() },
        { id: "demo-v2", project_id: "demo-p1", filename: "tech_review_unboxing.mp4", file_path: "C:\\videos\\unboxing.mp4", duration: 320, width: 1920, height: 1080, fps: 60, status: "processing", created_at: new Date().toISOString() }
      ];
      setVideos(mockVideos);
    }
  }, [currentProject, isBackendOnline]);

  // Fetch clips when selected video changes
  useEffect(() => {
    if (selectedVideo && isBackendOnline) {
      fetchClips();
    } else if (selectedVideo && !isBackendOnline) {
      const mockClips = [
        {
          id: "demo-c1",
          video_id: selectedVideo.id,
          title: "The secret to AI automation 🤯",
          start_time: 12.5,
          end_time: 35.2,
          duration: 22.7,
          score: 95,
          explanation: "Exciting moment where speaker explains local LLM deployment speed.",
          status: "ready_to_render",
          subtitles: [
            { word: "Welcome", start: 12.5, end: 12.8 },
            { word: "to", start: 12.8, end: 13.0 },
            { word: "local", start: 13.0, end: 13.4 },
            { word: "artificial", start: 13.4, end: 13.9 },
            { word: "intelligence", start: 13.9, end: 14.5 }
          ],
          subtitle_style: { font_family: "Montserrat", font_size: 28, primary_color: "#FFFFFF", accent_color: "#FF0055", outline_color: "#000000", margin_v: 140 },
          created_at: new Date().toISOString()
        },
        {
          id: "demo-c2",
          video_id: selectedVideo.id,
          title: "How face tracking works",
          start_time: 65.0,
          end_time: 85.0,
          duration: 20.0,
          score: 87,
          explanation: "High visual motion demonstrating video scaling techniques.",
          status: "completed",
          file_path: "https://assets.mixkit.co/videos/preview/mixkit-man-working-on-his-laptop-34288-large.mp4",
          subtitles: [
            { word: "Our", start: 65.0, end: 65.2 },
            { word: "face", start: 65.2, end: 65.5 },
            { word: "tracking", start: 65.5, end: 65.9 },
            { word: "centers", start: 65.9, end: 66.2 },
            { word: "automatically", start: 66.2, end: 67.0 }
          ],
          subtitle_style: { font_family: "Montserrat", font_size: 28, primary_color: "#FFFFFF", accent_color: "#FF0055", outline_color: "#000000", margin_v: 140 },
          created_at: new Date().toISOString()
        }
      ];
      setClips(mockClips);
    }
  }, [selectedVideo]);

  const fetchVideos = async () => {
    if (!currentProject) return;
    try {
      const res = await fetch(`${API_URL}/api/projects/${currentProject.id}/videos`);
      const data = await res.json();
      setVideos(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchClips = async () => {
    if (!selectedVideo) return;
    try {
      const res = await fetch(`${API_URL}/api/videos/${selectedVideo.id}/clips`);
      const data = await res.json();
      setClips(data);
    } catch (e) {
      console.error(e);
    }
  };

  // Create Project
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName) return;
    
    if (isBackendOnline) {
      try {
        const res = await fetch(`${API_URL}/api/projects`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: newProjectName, description: newProjectDesc })
        });
        const data = await res.json();
        setProjects([data, ...projects]);
        setCurrentProject(data);
        setNewProjectName("");
        setNewProjectDesc("");
      } catch (e) {
        console.error(e);
      }
    } else {
      const newProj = {
        id: `demo-${Date.now()}`,
        name: newProjectName,
        description: newProjectDesc,
        created_at: new Date().toISOString()
      };
      setProjects([newProj, ...projects]);
      setCurrentProject(newProj);
      setNewProjectName("");
      setNewProjectDesc("");
    }
  };

  // Import Video File (Upload)
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !currentProject) return;
    
    const formData = new FormData();
    formData.append("file", file);
    
    setUploadProgress(10);
    try {
      const res = await fetch(`${API_URL}/api/projects/${currentProject.id}/videos/upload`, {
        method: "POST",
        body: formData
      });
      if (res.status === 200) {
        setUploadProgress(100);
        setTimeout(() => setUploadProgress(null), 2000);
        fetchVideos();
        setActiveTab("ai-processing");
      }
    } catch (e) {
      console.error(e);
      setUploadProgress(null);
    }
  };

  // Import Local Path
  const handleLocalPathImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localVideoPath || !currentProject) return;
    
    if (isBackendOnline) {
      try {
        setIsLoading(true);
        const res = await fetch(`${API_URL}/api/projects/${currentProject.id}/videos/import-path`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_path: localVideoPath })
        });
        if (res.status === 200) {
          setLocalVideoPath("");
          fetchVideos();
          setActiveTab("ai-processing");
        } else {
          const err = await res.json();
          alert(`Error: ${err.detail}`);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    } else {
      const mockVid = {
        id: `demo-${Date.now()}`,
        project_id: currentProject.id,
        filename: localVideoPath.split("\\").pop() || "local_video.mp4",
        file_path: localVideoPath,
        duration: 120,
        width: 1920,
        height: 1080,
        fps: 30,
        status: "processing",
        created_at: new Date().toISOString()
      };
      setVideos([mockVid, ...videos]);
      setLocalVideoPath("");
      setActiveTab("ai-processing");
    }
  };

  // Select clip for editing
  const handleOpenEditor = (clip: Clip) => {
    setSelectedClip(clip);
    setClipTitle(clip.title);
    setClipStart(clip.start_time);
    setClipEnd(clip.end_time);
    setClipSubtitles(clip.subtitles);
    
    let parsedStyle = clip.subtitle_style;
    if (typeof parsedStyle === "string") {
      try {
        parsedStyle = JSON.parse(parsedStyle);
      } catch {
        parsedStyle = subtitleStyle;
      }
    }
    setSubtitleStyle(parsedStyle || subtitleStyle);
    
    setActiveTab("editor");
  };

  // Render Clip Trigger
  const handleRenderClip = async () => {
    if (!selectedClip) return;
    
    // Save settings and subtitles first
    if (isBackendOnline) {
      try {
        // Save updates
        await fetch(`${API_URL}/api/clips/${selectedClip.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: clipTitle,
            start_time: clipStart,
            end_time: clipEnd,
            subtitles: clipSubtitles,
            subtitle_style: subtitleStyle
          })
        });
        
        // Trigger render
        await fetch(`${API_URL}/api/clips/${selectedClip.id}/render`, {
          method: "POST"
        });
        
        alert("Render started in background! Check back in generated clips.");
        setSelectedClip(null);
        setActiveTab("generated-clips");
        fetchClips();
      } catch (e) {
        console.error(e);
      }
    } else {
      // Mock render update
      const updatedClips = clips.map(c => {
        if (c.id === selectedClip.id) {
          return {
            ...c,
            title: clipTitle,
            start_time: clipStart,
            end_time: clipEnd,
            subtitles: clipSubtitles,
            subtitle_style: subtitleStyle,
            status: "completed",
            file_path: "https://assets.mixkit.co/videos/preview/mixkit-man-working-on-his-laptop-34288-large.mp4"
          };
        }
        return c;
      });
      setClips(updatedClips);
      alert("Demo render completed instantly!");
      setSelectedClip(null);
      setActiveTab("generated-clips");
    }
  };

  // Helper for subtitle rendering formatting
  const handleWordChange = (idx: number, field: string, val: any) => {
    const updated = [...clipSubtitles];
    updated[idx] = { ...updated[idx], [field]: val };
    setClipSubtitles(updated);
  };

  return (
    <div className="flex min-h-screen text-slate-100 font-sans">
      
      {/* --- Sidebar --- */}
      <aside className="w-64 glass-panel border-r border-slate-800 flex flex-col shrink-0">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FF0055] to-[#00F0FF] flex items-center justify-center shadow-lg shadow-pink-500/20">
            <Sparkles className="w-6 h-6 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="font-extrabold text-lg leading-none text-white tracking-wide">ClipForge AI</h1>
            <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Local Engine</span>
          </div>
        </div>

        {/* Project Selector */}
        <div className="px-4 py-4 border-b border-slate-800">
          <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2 block">Active Project</label>
          <div className="relative">
            <select 
              value={currentProject?.id || ""} 
              onChange={(e) => {
                const found = projects.find(p => p.id === e.target.value);
                if (found) setCurrentProject(found);
              }}
              className="w-full bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none focus:border-[#FF0055] transition-all cursor-pointer appearance-none"
            >
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
              {projects.length === 0 && <option>No projects</option>}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
              <ChevronRight className="w-4 h-4 transform rotate-90" />
            </div>
          </div>
        </div>

        {/* Menu Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {[
            { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
            { id: "projects", label: "Projects", icon: FolderKanban },
            { id: "channels", label: "Channels", icon: Radio },
            { id: "video-library", label: "Video Library", icon: Video },
            { id: "ai-processing", label: "AI Processing", icon: Cpu },
            { id: "generated-clips", label: "Generated Clips", icon: Film },
            { id: "upload-queue", label: "Upload Queue", icon: Share2 },
            { id: "scheduler", label: "Scheduler", icon: Calendar },
            { id: "analytics", label: "Analytics", icon: BarChart3 },
            { id: "templates", label: "Templates", icon: Palette },
            { id: "brand-settings", label: "Brand Settings", icon: Sliders },
            { id: "automation", label: "Automation", icon: Scissors },
            { id: "settings", label: "Settings", icon: Settings },
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                  active 
                    ? "bg-gradient-to-r from-[#FF0055]/10 to-[#00F0FF]/5 text-white border-l-4 border-[#FF0055] pl-3" 
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? "text-[#FF0055]" : ""}`} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Connection Status Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/20 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-semibold">Backend Engine:</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isBackendOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
              <span className={`font-bold ${isBackendOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isBackendOnline ? 'ONLINE' : 'SANDBOX'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* --- Main Workspace --- */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#0b0c10]/20 overflow-y-auto">
        
        {/* Top Header */}
        <header className="h-16 border-b border-slate-800 px-8 flex items-center justify-between shrink-0 bg-slate-950/20 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-white capitalize">{activeTab.replace("-", " ")}</h2>
            {!isBackendOnline && (
              <span className="text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold px-2 py-0.5 rounded-full">
                Demo Sandbox Mode
              </span>
            )}
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">AI Credits:</span>
              <span className="text-sm font-bold bg-slate-800 px-3 py-1 rounded-lg border border-slate-700 text-[#00F0FF]">
                Unlimited (Local)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Storage Used:</span>
              <span className="text-sm font-bold text-slate-200">
                14.2 GB
              </span>
            </div>
          </div>
        </header>

        {/* Page Content Render */}
        <div className="p-8 flex-1">
          
          {/* 1. DASHBOARD VIEW */}
          {activeTab === "dashboard" && (
            <div className="space-y-8">
              {/* Overview Metrics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                  { label: "Videos Imported", value: videos.length, icon: Video, color: "from-blue-500 to-indigo-600" },
                  { label: "Videos Processing", value: videos.filter(v => v.status === "processing").length, icon: Cpu, color: "from-amber-500 to-orange-600", pulse: true },
                  { label: "Clips Generated", value: clips.length, icon: Film, color: "from-[#FF0055] to-pink-600" },
                  { label: "Today's Uploads", value: 3, icon: Share2, color: "from-[#00F0FF] to-cyan-600" }
                ].map((card, i) => {
                  const Icon = card.icon;
                  return (
                    <div key={i} className="glass-panel rounded-2xl p-6 relative overflow-hidden group">
                      <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br opacity-5 rounded-full blur-xl group-hover:scale-125 transition-transform duration-500"></div>
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-xs text-slate-400 font-bold tracking-wider uppercase">{card.label}</span>
                          <h3 className="text-3xl font-black mt-2 text-white">{card.value}</h3>
                        </div>
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center shadow-lg`}>
                          <Icon className={`w-5 h-5 text-white ${card.pulse ? 'animate-spin' : ''}`} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Central Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                {/* Recent Videos List */}
                <div className="lg:col-span-2 glass-panel rounded-2xl p-6 flex flex-col">
                  <h3 className="text-base font-bold text-white mb-6">Recent Long-form Videos</h3>
                  <div className="space-y-4 flex-1">
                    {videos.map(v => (
                      <div 
                        key={v.id} 
                        onClick={() => { setSelectedVideo(v); setActiveTab("generated-clips"); }}
                        className="p-4 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-900/30 hover:bg-slate-900/50 flex items-center justify-between transition-all cursor-pointer group"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-[#FF0055] transition-colors">
                            <Video className="w-5 h-5" />
                          </div>
                          <div>
                            <h4 className="font-bold text-sm text-slate-200 group-hover:text-white transition-colors">{v.filename}</h4>
                            <span className="text-xs text-slate-500 mt-0.5 block">{v.file_path}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                            v.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            v.status === 'processing' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' :
                            'bg-slate-800 text-slate-400'
                          }`}>
                            {v.status}
                          </span>
                          <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
                        </div>
                      </div>
                    ))}
                    {videos.length === 0 && (
                      <div className="text-center py-12 text-slate-500 text-sm">
                        No videos imported yet. Go to Video Library to add one!
                      </div>
                    )}
                  </div>
                </div>

                {/* Queue Monitor card */}
                <div className="glass-panel rounded-2xl p-6">
                  <h3 className="text-base font-bold text-white mb-6">Pipeline Queue</h3>
                  <div className="space-y-4">
                    {[
                      { label: "Processing Scene Cuts", desc: "Extracting color histograms", time: "1 min remaining", status: "active" },
                      { label: "Audio Peak Check", desc: "Volume analytics", time: "Waiting", status: "queued" },
                      { label: "Speech Transcription", desc: "Whisper audio conversion", time: "Waiting", status: "queued" },
                      { label: "Ollama Moment Assessment", desc: "Viral moment scanning", time: "Waiting", status: "queued" }
                    ].map((item, idx) => (
                      <div key={idx} className="flex gap-4 items-start">
                        <div className="flex flex-col items-center">
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                            item.status === 'active' ? 'bg-[#FF0055] text-white' : 'bg-slate-800 text-slate-500'
                          }`}>
                            {idx + 1}
                          </div>
                          {idx < 3 && <div className="w-0.5 h-10 bg-slate-800 my-1"></div>}
                        </div>
                        <div>
                          <h4 className={`text-sm font-semibold ${item.status === 'active' ? 'text-white font-bold' : 'text-slate-400'}`}>{item.label}</h4>
                          <p className="text-xs text-slate-500 mt-0.5">{item.desc}</p>
                          {item.status === 'active' && (
                            <span className="text-[10px] text-[#00F0FF] mt-1 block font-bold">{item.time}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 2. PROJECTS VIEW */}
          {activeTab === "projects" && (
            <div className="space-y-8 max-w-4xl">
              <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-6">Create New Project</h3>
                <form onSubmit={handleCreateProject} className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Project Name</label>
                    <input 
                      type="text" 
                      placeholder="e.g. My Tech Channel"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:border-[#FF0055] transition-all"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Description</label>
                    <textarea 
                      placeholder="Short notes about templates or brands..."
                      rows={3}
                      value={newProjectDesc}
                      onChange={(e) => setNewProjectDesc(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:border-[#FF0055] transition-all"
                    />
                  </div>
                  <button 
                    type="submit"
                    className="bg-gradient-to-r from-[#FF0055] to-pink-600 hover:from-pink-600 hover:to-pink-700 text-white font-bold text-sm px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all shadow-lg shadow-pink-500/20 cursor-pointer"
                  >
                    <Plus className="w-4 h-4" /> Create Project
                  </button>
                </form>
              </div>

              {/* Project Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {projects.map(p => (
                  <div 
                    key={p.id}
                    onClick={() => setCurrentProject(p)}
                    className={`glass-panel rounded-2xl p-6 cursor-pointer border transition-all ${
                      currentProject?.id === p.id ? "border-[#FF0055] shadow-lg shadow-pink-500/5" : "border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-bold text-base text-white">{p.name}</h4>
                        <p className="text-xs text-slate-400 mt-2">{p.description || "No description provided."}</p>
                      </div>
                      {currentProject?.id === p.id && (
                        <span className="w-5 h-5 rounded-full bg-[#FF0055] flex items-center justify-center">
                          <Check className="w-3 h-3 text-white" />
                        </span>
                      )}
                    </div>
                    <div className="mt-6 flex items-center gap-4 text-xs text-slate-500 border-t border-slate-800/50 pt-4">
                      <span>Created: {new Date(p.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. CHANNELS VIEW */}
          {activeTab === "channels" && (
            <div className="space-y-8 max-w-4xl">
              <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-2">Connected Channels</h3>
                <p className="text-xs text-slate-400 mb-6">Manage API configurations and accounts linked to this project.</p>
                
                <div className="space-y-4">
                  {[
                    { name: "YouTube Shorts Channel", platform: "YouTube", status: "connected", account: "CodeBytes Shorts" },
                    { name: "Instagram Reels", platform: "Instagram", status: "connected", account: "@codebytes_ai" },
                    { name: "TikTok Account", platform: "TikTok", status: "disconnected", account: "Not linked" },
                    { name: "LinkedIn Page", platform: "LinkedIn", status: "disconnected", account: "Not linked" }
                  ].map((chan, idx) => (
                    <div key={idx} className="p-4 rounded-xl border border-slate-800 bg-slate-900/20 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center font-bold text-xs text-slate-300">
                          {chan.platform[0]}
                        </div>
                        <div>
                          <h4 className="font-bold text-sm text-slate-200">{chan.name}</h4>
                          <span className="text-xs text-slate-500 mt-0.5 block">{chan.account}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          chan.status === 'connected' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {chan.status}
                        </span>
                        <button className="text-xs text-[#00F0FF] hover:underline font-bold">
                          {chan.status === 'connected' ? 'Configure' : 'Connect'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 4. VIDEO LIBRARY */}
          {activeTab === "video-library" && (
            <div className="space-y-8 max-w-4xl">
              {/* Import Options Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                
                {/* Drag-drop Upload */}
                <div className="glass-panel rounded-2xl p-6 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 hover:border-[#FF0055]/30 hover:bg-slate-900/10 transition-all group relative p-12 text-center">
                  <Upload className="w-12 h-12 text-slate-500 group-hover:text-[#FF0055] transition-colors mb-4" />
                  <h4 className="font-bold text-sm text-white">Drag & drop video file</h4>
                  <p className="text-xs text-slate-500 mt-1 max-w-[200px]">MP4, MOV up to 2GB will be copied to local imports</p>
                  
                  <input 
                    type="file" 
                    accept="video/*" 
                    onChange={handleFileUpload}
                    className="absolute inset-0 opacity-0 cursor-pointer" 
                  />
                  {uploadProgress !== null && (
                    <div className="absolute inset-0 bg-slate-950/90 rounded-2xl flex flex-col items-center justify-center p-6">
                      <Clock className="w-8 h-8 text-[#FF0055] animate-spin mb-2" />
                      <span className="text-xs font-bold text-slate-300">Copying video file to server...</span>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-4 overflow-hidden max-w-xs">
                        <div className="bg-[#FF0055] h-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Local Path Input */}
                <div className="glass-panel rounded-2xl p-6 flex flex-col justify-center">
                  <h4 className="font-bold text-sm text-white mb-2 flex items-center gap-2">
                    <FolderKanban className="w-4 h-4 text-[#00F0FF]" /> Import Local Path
                  </h4>
                  <p className="text-xs text-slate-500 mb-6">Type the full path of a local video file. ClipForge will import it instantly without rendering wait.</p>
                  
                  <form onSubmit={handleLocalPathImport} className="space-y-4">
                    <input 
                      type="text" 
                      placeholder="e.g. C:\Users\pasam\Videos\my_podcast.mp4"
                      value={localVideoPath}
                      onChange={(e) => setLocalVideoPath(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:border-[#FF0055] transition-all font-mono text-xs"
                    />
                    <button 
                      type="submit" 
                      disabled={isLoading}
                      className="w-full bg-slate-800 hover:bg-slate-700 text-[#00F0FF] font-bold text-xs py-2.5 rounded-lg transition-colors cursor-pointer"
                    >
                      {isLoading ? "Importing..." : "Scan & Import File"}
                    </button>
                  </form>
                </div>
              </div>

              {/* Imported Videos List */}
              <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-6">Imported Video Files</h3>
                <div className="space-y-4">
                  {videos.map(v => (
                    <div 
                      key={v.id}
                      onClick={() => { setSelectedVideo(v); setActiveTab("generated-clips"); }}
                      className="p-4 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-900/20 hover:bg-slate-900/40 flex items-center justify-between cursor-pointer transition-all"
                    >
                      <div>
                        <h4 className="font-bold text-sm text-slate-200">{v.filename}</h4>
                        <span className="text-xs text-slate-500 block mt-1 font-mono">{v.file_path}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        {v.duration ? (
                          <span className="text-xs font-semibold text-slate-400">
                            {Math.floor(v.duration / 60)}m {Math.floor(v.duration % 60)}s
                          </span>
                        ) : null}
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                          v.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          v.status === 'processing' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' :
                          'bg-slate-800 text-slate-400'
                        }`}>
                          {v.status}
                        </span>
                      </div>
                    </div>
                  ))}
                  {videos.length === 0 && (
                    <div className="text-center py-12 text-slate-500 text-sm">
                      No video files imported yet. Select a file or enter a local path above to start!
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 5. AI PROCESSING MONITOR */}
          {activeTab === "ai-processing" && (
            <div className="space-y-8 max-w-4xl">
              <div className="glass-panel rounded-2xl p-8 text-center relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#FF0055] to-[#00F0FF] animate-pulse"></div>
                
                <Cpu className="w-16 h-16 text-[#FF0055] mx-auto mb-6 animate-pulse" />
                <h3 className="text-xl font-bold text-white mb-2">AI Processing Pipeline</h3>
                <p className="text-sm text-slate-400 max-w-md mx-auto mb-8">
                  The local engine is analyzing your file. We run local Whisper models, OpenCV face tracking, and local Ollama inference models.
                </p>

                {/* Pipeline visual steps */}
                <div className="max-w-2xl mx-auto space-y-6 text-left">
                  {[
                    { label: "Step 1: Reading Video Metadata", desc: "Checking file dimensions, framerate and audio format.", status: "completed" },
                    { label: "Step 2: Color Histogram scene cuts", desc: "Scanning frames at intervals to find logical cut points.", status: "completed" },
                    { label: "Step 3: Speech-To-Text Whisper Sync", desc: "Generating word-by-word timestamp coordinates.", status: "active" },
                    { label: "Step 4: Ollama Moment Valuation", desc: "Running local Llama3 model prompts to rank segments.", status: "pending" },
                    { label: "Step 5: Crop Optimization", desc: "Tracking speaker face paths and preparing clipping instructions.", status: "pending" }
                  ].map((step, i) => (
                    <div key={i} className="flex gap-4 p-4 rounded-xl border border-slate-800/40 bg-slate-900/10">
                      <div className="mt-1">
                        {step.status === "completed" && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                        {step.status === "active" && <RefreshCw className="w-5 h-5 text-[#FF0055] animate-spin" />}
                        {step.status === "pending" && <Clock className="w-5 h-5 text-slate-600" />}
                      </div>
                      <div>
                        <h4 className={`text-sm font-bold ${step.status === 'active' ? 'text-white' : step.status === 'completed' ? 'text-slate-300' : 'text-slate-600'}`}>{step.label}</h4>
                        <p className={`text-xs mt-0.5 ${step.status === 'pending' ? 'text-slate-700' : 'text-slate-500'}`}>{step.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-8 pt-6 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500 max-w-2xl mx-auto">
                  <span>Engine: Python 3.12 (Local)</span>
                  <span>Whisper Mode: CPU tiny</span>
                  <span>LLM: llama3 (Ollama)</span>
                </div>
              </div>
            </div>
          )}

          {/* 6. GENERATED CLIPS VIEW */}
          {activeTab === "generated-clips" && (
            <div className="space-y-8">
              {/* Video Selector header */}
              <div className="glass-panel rounded-xl p-4 flex flex-wrap gap-4 items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 font-bold">Select Source Video:</span>
                  <select 
                    value={selectedVideo?.id || ""}
                    onChange={(e) => {
                      const found = videos.find(v => v.id === e.target.value);
                      if (found) setSelectedVideo(found);
                    }}
                    className="bg-slate-900 border border-slate-850 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none"
                  >
                    <option value="">-- Choose Video --</option>
                    {videos.map(v => (
                      <option key={v.id} value={v.id}>{v.filename}</option>
                    ))}
                  </select>
                </div>
                
                {selectedVideo && (
                  <span className="text-xs text-slate-400">
                    Showing <strong className="text-white">{clips.length}</strong> clip proposals generated automatically.
                  </span>
                )}
              </div>

              {/* Clip grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {clips.map(c => (
                  <div key={c.id} className="glass-panel rounded-2xl overflow-hidden flex flex-col group border border-slate-800 hover:border-pink-500/20 transition-all">
                    
                    {/* Visual Card Top */}
                    <div className="h-44 bg-slate-900 relative flex items-center justify-center overflow-hidden">
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent z-10"></div>
                      
                      {/* Grid representation or video player */}
                      <Film className="w-12 h-12 text-slate-700 group-hover:scale-110 transition-transform duration-300" />
                      
                      {/* Virality Score Badge */}
                      <div className="absolute top-4 left-4 bg-slate-950/80 border border-slate-800 px-3 py-1 rounded-full text-xs font-bold text-[#FF0055] flex items-center gap-1 z-20">
                        <Sparkles className="w-3.5 h-3.5" /> {c.score}% Virality
                      </div>

                      {/* Duration badge */}
                      <div className="absolute bottom-4 right-4 bg-slate-950/80 px-2 py-0.5 rounded text-[10px] font-bold text-slate-300 z-20">
                        {c.duration.toFixed(1)}s
                      </div>
                    </div>

                    {/* Card details */}
                    <div className="p-6 flex-1 flex flex-col justify-between">
                      <div>
                        <h4 className="font-bold text-sm text-slate-100 group-hover:text-white transition-colors line-clamp-1">{c.title}</h4>
                        <p className="text-xs text-slate-500 mt-2 line-clamp-2">{c.explanation}</p>
                        
                        <div className="mt-4 flex items-center gap-4 text-[10px] text-slate-500">
                          <span>Start: {c.start_time.toFixed(1)}s</span>
                          <span>End: {c.end_time.toFixed(1)}s</span>
                        </div>
                      </div>

                      <div className="mt-6 pt-4 border-t border-slate-800/50 flex items-center justify-between">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          c.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          c.status === 'rendering' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' :
                          'bg-slate-800 text-slate-400'
                        }`}>
                          {c.status.replace("_", " ")}
                        </span>
                        
                        <button 
                          onClick={() => handleOpenEditor(c)}
                          className="bg-slate-800 hover:bg-[#FF0055]/10 border border-slate-700 hover:border-[#FF0055]/30 hover:text-white px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1 cursor-pointer"
                        >
                          <Edit3 className="w-3.5 h-3.5 text-[#FF0055]" /> Review & Edit
                        </button>
                      </div>
                    </div>
                  </div>
                ))}

                {(!selectedVideo) && (
                  <div className="col-span-full text-center py-20 glass-panel rounded-2xl text-slate-500">
                    Please select a source video from the dropdown above to load clips.
                  </div>
                )}
                
                {selectedVideo && clips.length === 0 && (
                  <div className="col-span-full text-center py-20 glass-panel rounded-2xl text-slate-500">
                    No clip proposals found for this video.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 7. CLIP REVIEW & EDITOR VIEW (CRITICAL PATH) */}
          {activeTab === "editor" && selectedClip && (
            <div className="space-y-8 max-w-6xl mx-auto">
              
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => { setSelectedClip(null); setActiveTab("generated-clips"); }}
                    className="text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg"
                  >
                    &larr; Back to Clips
                  </button>
                  <h3 className="text-base font-bold text-white">{clipTitle}</h3>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={handleRenderClip}
                    className="bg-gradient-to-r from-[#FF0055] to-pink-600 hover:from-pink-600 hover:to-pink-700 text-white px-6 py-2 rounded-lg text-xs font-bold transition-colors cursor-pointer shadow-lg shadow-pink-500/10"
                  >
                    Render Clip (Burn Subtitles)
                  </button>
                </div>
              </div>

              {/* Editor Workspace */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                {/* 1. Left Column: Player & Timing (Col 5) */}
                <div className="lg:col-span-5 space-y-6">
                  {/* Phone player frame */}
                  <div className="aspect-[9/16] max-h-[500px] mx-auto bg-slate-950 rounded-[32px] border-4 border-slate-800 shadow-2xl relative overflow-hidden flex flex-col justify-center items-center">
                    
                    {/* Rendered Player / Original Source Mock */}
                    {selectedClip.file_path || isBackendOnline ? (
                      <video 
                        src={selectedClip.file_path ? (selectedClip.file_path.startsWith("http") ? selectedClip.file_path : `${API_URL}${selectedClip.file_path}`) : ""}
                        controls
                        className="w-full h-full object-cover"
                        poster="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600&auto=format&fit=crop"
                      />
                    ) : (
                      <div className="text-center p-6 space-y-4">
                        <Film className="w-12 h-12 text-[#FF0055] mx-auto animate-pulse" />
                        <h4 className="text-sm font-bold text-white">Clip Not Rendered Yet</h4>
                        <p className="text-xs text-slate-500 max-w-[200px] mx-auto">Render clip using FFmpeg to burn dynamic word subtitles and crop to 9:16 vertical.</p>
                      </div>
                    )}

                    {/* Styled Subtitle Simulation Overlay (Real-time Preview) */}
                    {!selectedClip.file_path && (
                      <div 
                        className="absolute text-center w-full px-6 font-extrabold select-none pointer-events-none drop-shadow-md"
                        style={{
                          bottom: `${subtitleStyle.margin_v / 2}px`,
                          fontFamily: subtitleStyle.font_family,
                          fontSize: `${subtitleStyle.font_size / 2}px`,
                          color: subtitleStyle.primary_color,
                          WebkitTextStroke: `1px ${subtitleStyle.outline_color}`,
                        }}
                      >
                        <span style={{ color: subtitleStyle.accent_color }}>AI Captions</span> on Screen
                      </div>
                    )}
                  </div>

                  {/* Range Boundaries inputs */}
                  <div className="glass-panel rounded-2xl p-6 space-y-4">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Timing Boundaries</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-1">Start Time (sec)</label>
                        <input 
                          type="number" 
                          step="0.1"
                          value={clipStart}
                          onChange={(e) => setClipStart(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-[#FF0055]"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-1">End Time (sec)</label>
                        <input 
                          type="number" 
                          step="0.1"
                          value={clipEnd}
                          onChange={(e) => setClipEnd(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-[#FF0055]"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. Right Column: Subtitle Word Grid & Styles (Col 7) */}
                <div className="lg:col-span-7 space-y-6">
                  
                  {/* Style Presets */}
                  <div className="glass-panel rounded-2xl p-6 space-y-4">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Subtitle Styling</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      
                      {/* Font selector */}
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-1.5">Font Family</label>
                        <select 
                          value={subtitleStyle.font_family}
                          onChange={(e) => setSubtitleStyle({ ...subtitleStyle, font_family: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none cursor-pointer"
                        >
                          <option value="Montserrat">Montserrat (Bold)</option>
                          <option value="Outfit">Outfit (Sleek)</option>
                          <option value="Impact">Impact (Classic Meme)</option>
                          <option value="Arial">Arial (Standard)</option>
                        </select>
                      </div>

                      {/* Font size */}
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-1.5">Font Size</label>
                        <input 
                          type="number" 
                          value={subtitleStyle.font_size}
                          onChange={(e) => setSubtitleStyle({ ...subtitleStyle, font_size: parseInt(e.target.value) || 24 })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none"
                        />
                      </div>

                      {/* Color selections */}
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-1.5">Primary Color (Base)</label>
                        <div className="flex gap-2">
                          <input 
                            type="color" 
                            value={subtitleStyle.primary_color}
                            onChange={(e) => setSubtitleStyle({ ...subtitleStyle, primary_color: e.target.value })}
                            className="bg-transparent border-0 w-8 h-8 rounded cursor-pointer"
                          />
                          <input 
                            type="text"
                            value={subtitleStyle.primary_color}
                            onChange={(e) => setSubtitleStyle({ ...subtitleStyle, primary_color: e.target.value })}
                            className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1 text-xs text-slate-200"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-1.5">Accent Color (Highlight)</label>
                        <div className="flex gap-2">
                          <input 
                            type="color" 
                            value={subtitleStyle.accent_color}
                            onChange={(e) => setSubtitleStyle({ ...subtitleStyle, accent_color: e.target.value })}
                            className="bg-transparent border-0 w-8 h-8 rounded cursor-pointer"
                          />
                          <input 
                            type="text"
                            value={subtitleStyle.accent_color}
                            onChange={(e) => setSubtitleStyle({ ...subtitleStyle, accent_color: e.target.value })}
                            className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1 text-xs text-slate-200"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Word Sync list */}
                  <div className="glass-panel rounded-2xl p-6 flex flex-col h-[350px]">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-4">Word-by-word Subtitle Timestamps</h4>
                    <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                      {clipSubtitles.map((word, idx) => (
                        <div key={idx} className="flex gap-3 items-center p-2 rounded-lg bg-slate-900/40 border border-slate-800/40">
                          <input 
                            type="text" 
                            value={word.word}
                            onChange={(e) => handleWordChange(idx, "word", e.target.value)}
                            className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1 text-xs text-slate-200 focus:border-[#FF0055] font-semibold"
                          />
                          <div className="flex gap-2 shrink-0">
                            <div>
                              <input 
                                type="number" 
                                step="0.05"
                                value={word.start}
                                onChange={(e) => handleWordChange(idx, "start", parseFloat(e.target.value) || 0)}
                                className="w-16 bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-[10px] text-slate-400 font-mono text-center"
                              />
                            </div>
                            <span className="text-slate-600 text-xs self-center">to</span>
                            <div>
                              <input 
                                type="number" 
                                step="0.05"
                                value={word.end}
                                onChange={(e) => handleWordChange(idx, "end", parseFloat(e.target.value) || 0)}
                                className="w-16 bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-[10px] text-slate-400 font-mono text-center"
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                      {clipSubtitles.length === 0 && (
                        <div className="text-center py-12 text-slate-600 text-xs">
                          No transcription words in this clip.
                        </div>
                      )}
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* 8. UPLOAD QUEUE */}
          {activeTab === "upload-queue" && (
            <div className="space-y-8 max-w-4xl">
              <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-6">Upload Publishing Queue</h3>
                <div className="space-y-4">
                  {[
                    { title: "AI tools everyone misses", platform: "YouTube", date: "Today 14:30", status: "completed" },
                    { title: "Local models are the future", platform: "Instagram", date: "Today 18:00", status: "uploading" },
                    { title: "FFmpeg cropping hack", platform: "TikTok", date: "Tomorrow 10:00", status: "scheduled" }
                  ].map((job, idx) => (
                    <div key={idx} className="p-4 rounded-xl border border-slate-800 bg-slate-900/20 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-slate-400">
                          {job.platform[0]}
                        </div>
                        <div>
                          <h4 className="font-bold text-sm text-slate-200">{job.title}</h4>
                          <span className="text-xs text-slate-500 mt-1 block">Publish: {job.date}</span>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                        job.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        job.status === 'uploading' ? 'bg-[#FF0055]/10 text-[#FF0055] border border-[#FF0055]/20 animate-pulse' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {job.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 9. SCHEDULER VIEW */}
          {activeTab === "scheduler" && (
            <div className="space-y-8">
              <div className="flex justify-between items-center">
                <h3 className="text-base font-bold text-white">Calendar Planner</h3>
                <button 
                  onClick={() => alert("Scheduled auto-publishing successfully!")}
                  className="bg-slate-800 hover:bg-slate-700 text-[#00F0FF] border border-slate-700 font-bold text-xs px-4 py-2 rounded-lg cursor-pointer"
                >
                  Apply Publishing Times
                </button>
              </div>

              {/* Calendar Grid Representation */}
              <div className="grid grid-cols-7 gap-4">
                {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((day, i) => (
                  <div key={i} className="glass-panel rounded-2xl p-4 min-h-[250px] flex flex-col">
                    <span className="text-xs font-bold text-slate-400 border-b border-slate-800/80 pb-2 mb-3 block">{day}</span>
                    
                    {/* Simulated Clips dropped */}
                    <div className="space-y-3 flex-1">
                      {i === 2 && (
                        <div className="p-2 rounded bg-slate-900 border-l-2 border-[#FF0555] text-[10px]">
                          <span className="font-bold text-[#FF0555]">14:30</span>
                          <p className="text-slate-300 font-semibold truncate">AI tools highlights</p>
                          <span className="text-slate-500">YouTube</span>
                        </div>
                      )}
                      {i === 3 && (
                        <div className="p-2 rounded bg-slate-900 border-l-2 border-[#00F0FF] text-[10px]">
                          <span className="font-bold text-[#00F0FF]">18:00</span>
                          <p className="text-slate-300 font-semibold truncate">Local model hack</p>
                          <span className="text-slate-500">TikTok</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 10. ANALYTICS VIEW */}
          {activeTab === "analytics" && (
            <div className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  { label: "Total Views", value: "318.4K", change: "+14.2%" },
                  { label: "Avg CTR Score", value: "9.3%", change: "+0.8%" },
                  { label: "Audience Retention", value: "84.2%", change: "+2.1%" }
                ].map((stat, i) => (
                  <div key={i} className="glass-panel rounded-2xl p-6">
                    <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">{stat.label}</span>
                    <h3 className="text-3xl font-black mt-2 text-white">{stat.value}</h3>
                    <span className="text-xs text-emerald-400 font-bold mt-2 block">{stat.change} vs last week</span>
                  </div>
                ))}
              </div>

              {/* Beautiful custom SVG chart drawing */}
              <div className="glass-panel rounded-2xl p-6">
                <h4 className="text-sm font-bold text-white mb-6">Audience Growth & Retention Trends</h4>
                <div className="h-64 w-full relative">
                  <svg className="w-full h-full" viewBox="0 0 600 200" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="chartGlow" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#FF0055" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#FF0055" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    {/* Gridlines */}
                    <line x1="0" y1="50" x2="600" y2="50" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                    <line x1="0" y1="100" x2="600" y2="100" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                    <line x1="0" y1="150" x2="600" y2="150" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                    
                    {/* Area fill */}
                    <path 
                      d="M0,180 L50,150 L100,160 L150,110 L200,90 L250,120 L300,70 L350,60 L400,110 L450,40 L500,50 L550,20 L600,10 L600,200 L0,200 Z" 
                      fill="url(#chartGlow)" 
                    />
                    
                    {/* Line path */}
                    <path 
                      d="M0,180 L50,150 L100,160 L150,110 L200,90 L250,120 L300,70 L350,60 L400,110 L450,40 L500,50 L550,20 L600,10" 
                      fill="none" 
                      stroke="#FF0055" 
                      strokeWidth="3.5" 
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-x-0 bottom-0 flex justify-between px-2 text-[10px] text-slate-500 font-mono">
                    <span>Mon</span>
                    <span>Tue</span>
                    <span>Wed</span>
                    <span>Thu</span>
                    <span>Fri</span>
                    <span>Sat</span>
                    <span>Sun</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 11. TEMPLATES VIEW */}
          {activeTab === "templates" && (
            <div className="space-y-8 max-w-4xl">
              <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-2">Preset Caption Subtitle Templates</h3>
                <p className="text-xs text-slate-400 mb-6">Choose brand configurations for subtitles burnt onto horizontal clips.</p>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    { name: "Viral Neon", desc: "Montserrat, bold pink highlights", active: true },
                    { name: "Sleek Minimalist", desc: "Inter font, light blue borders", active: false },
                    { name: "Retro Sub", desc: "Impact font, yellow outline borders", active: false }
                  ].map((temp, idx) => (
                    <div 
                      key={idx} 
                      className={`p-6 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                        temp.active ? 'border-[#FF0055] bg-[#FF0055]/5' : 'border-slate-800 hover:border-slate-700 bg-slate-900/10'
                      }`}
                    >
                      <div>
                        <h4 className="font-bold text-sm text-slate-200">{temp.name}</h4>
                        <p className="text-xs text-slate-500 mt-2">{temp.desc}</p>
                      </div>
                      {temp.active ? (
                        <span className="text-xs font-bold text-[#FF0055] mt-6 flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> Selected Preset
                        </span>
                      ) : (
                        <button className="text-xs text-slate-400 hover:text-white font-bold mt-6 text-left">
                          Apply Style Preset
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 12. BRAND SETTINGS */}
          {activeTab === "brand-settings" && (
            <div className="space-y-8 max-w-3xl">
              <div className="glass-panel rounded-2xl p-6 space-y-6">
                <h3 className="text-base font-bold text-white mb-2">Brand Assets Configuration</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Logo Overlay (.png)</label>
                    <input 
                      type="text" 
                      placeholder="e.g. C:\brand\logo.png"
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Outro Video File (.mp4)</label>
                    <input 
                      type="text" 
                      placeholder="e.g. C:\brand\outro.mp4"
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Watermark Text</label>
                    <input 
                      type="text" 
                      value={brandPreset.watermark}
                      onChange={(e) => setBrandPreset({ ...brandPreset, watermark: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Brand Font Family</label>
                    <input 
                      type="text" 
                      value={brandPreset.font_family}
                      onChange={(e) => setBrandPreset({ ...brandPreset, font_family: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                </div>

                <button 
                  onClick={() => alert("Brand assets updated!")}
                  className="bg-gradient-to-r from-[#FF0055] to-pink-600 hover:from-pink-600 hover:to-pink-700 text-white font-bold text-xs px-6 py-2.5 rounded-lg transition-colors cursor-pointer"
                >
                  Save Brand Preset
                </button>
              </div>
            </div>
          )}

          {/* 13. AUTOMATION BUILDER */}
          {activeTab === "automation" && (
            <div className="space-y-8">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-base font-bold text-white">Visual Pipeline Flowchart</h3>
                  <p className="text-xs text-slate-400 mt-1">Configure automated steps that run as soon as a new video gets imported.</p>
                </div>
                <button 
                  onClick={() => alert("Automation workflow rule verified!")}
                  className="bg-slate-800 hover:bg-slate-750 border border-slate-700 text-[#00F0FF] font-bold text-xs px-4 py-2 rounded-lg cursor-pointer"
                >
                  Validate Nodes
                </button>
              </div>

              {/* Canvas flow layout */}
              <div className="glass-panel rounded-2xl p-8 min-h-[350px] flex items-center justify-center overflow-x-auto">
                <div className="flex items-center gap-6">
                  {automationNodes.map((node, idx) => (
                    <React.Fragment key={node.id}>
                      <div 
                        onClick={() => {
                          const updated = [...automationNodes];
                          updated[idx].active = !updated[idx].active;
                          setAutomationNodes(updated);
                        }}
                        className={`p-5 rounded-2xl border text-center select-none cursor-pointer transition-all duration-300 min-w-[140px] ${
                          node.active 
                            ? "bg-gradient-to-tr from-[#FF0055]/10 to-indigo-900/10 border-[#FF0055] shadow-lg shadow-pink-500/5 text-white" 
                            : "border-slate-800 bg-slate-950/20 text-slate-600"
                        }`}
                      >
                        <h4 className="font-bold text-xs">{node.label}</h4>
                        <span className="text-[9px] mt-2 block font-semibold uppercase tracking-wider">
                          {node.active ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      {idx < automationNodes.length - 1 && (
                        <div className="flex flex-col items-center">
                          <div className={`h-0.5 w-8 ${
                            node.active && automationNodes[idx + 1].active ? 'bg-gradient-to-r from-[#FF0055] to-[#00F0FF]' : 'bg-slate-800'
                          }`}></div>
                        </div>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 14. SETTINGS VIEW */}
          {activeTab === "settings" && (
            <div className="space-y-8 max-w-3xl">
              <div className="glass-panel rounded-2xl p-6 space-y-6">
                <h3 className="text-base font-bold text-white">System Settings</h3>
                
                <div className="space-y-4">
                  {/* Resolution and framerate */}
                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Default Clipping Resolution</label>
                    <select className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none w-full">
                      <option>1080x1920 (Vertical 9:16) - Recommended</option>
                      <option>1080x1080 (Square 1:1)</option>
                      <option>1920x1080 (Landscape 16:9)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Video Encoder Presets</label>
                    <select className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none w-full">
                      <option>libx264 (H.264 CPU encoder) - High compatibility</option>
                      <option>h264_nvenc (NVIDIA hardware encoder) - Extremely fast</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-2">Local Ollama Model for Scoring</label>
                    <select className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none w-full">
                      <option>llama3:latest (Detected)</option>
                      <option>qwen2.5:3b (Detected)</option>
                      <option>qwen3:4b (Detected)</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-800">
                  <button 
                    onClick={() => alert("Settings saved locally!")}
                    className="bg-gradient-to-r from-[#FF0055] to-pink-600 hover:from-pink-600 hover:to-pink-700 text-white font-bold text-xs px-6 py-2.5 rounded-lg transition-colors cursor-pointer"
                  >
                    Save Settings
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
