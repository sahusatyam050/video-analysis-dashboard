"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import {
  Video,
  UploadCloud,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  Loader2,
  Globe,
  Bot
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface AnalysisTask {
  id: string;
  video_name: string;
  status: string;
  progress: number;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTaskId = searchParams.get("task");
  
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  
  // Upload State
  const [activeTab, setActiveTab] = useState<"upload" | "crawl">("upload");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Crawl State
  const [crawlUrl, setCrawlUrl] = useState("");
  const [crawlDuration, setCrawlDuration] = useState(30);
  const [isCrawling, setIsCrawling] = useState(false);

  // Fetch past analyses
  const fetchTasks = async () => {
    try {
      const res = await axios.get("/api/analyses_detailed");
      setTasks(res.data);
    } catch (err) {
      console.error("Failed to fetch analyses", err);
    }
  };

  useEffect(() => {
    fetchTasks();
    // Poll every 5 seconds for status updates if any task is processing
    const interval = setInterval(() => {
      fetchTasks();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(0);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("/api/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total ?? 1));
          setUploadProgress(percentCompleted);
        }
      });
      const newTaskId = res.data.task_id;
      
      // Refresh list and navigate to new task
      await fetchTasks();
      router.push(`/?task=${newTaskId}`);
      
    } catch (err) {
      console.error("Upload failed", err);
      alert("Video upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };
  const handleCrawlStart = async () => {
    if (!crawlUrl) {
      alert("Please enter a URL to crawl.");
      return;
    }
    setIsCrawling(true);
    setUploadProgress(10); // Fake progress for crawling init
    try {
      const res = await axios.post("/api/crawl", {
        url: crawlUrl,
        duration: crawlDuration
      });
      const taskId = res.data.task_id;
      setUploadProgress(100);
      setIsCrawling(false);
      setCrawlUrl("");
      router.push(`/?task=${taskId}`);
    } catch (err) {
      console.error("Crawl failed", err);
      alert("Autonomous crawl failed. Please try again or check the backend logs.");
      setIsCrawling(false);
      setUploadProgress(0);
    }
  };
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "complete":
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
      case "processing":
        return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />;
      case "error":
        return <AlertCircle className="w-3.5 h-3.5 text-red-500" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="w-72 border-r border-slate-200 bg-white h-screen overflow-y-auto flex-shrink-0 pt-6 px-4 hidden md:block z-10 relative">
      
      {/* Main Navigation */}
      <div className="mb-6">
        <h3 className="px-4 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          MAIN
        </h3>
        <div className="space-y-1">
          <Link
            href="/"
            className={cn(
              "flex items-center gap-3 px-4 py-2 rounded-md text-sm font-medium transition-colors",
              !activeTaskId
                ? "bg-slate-100 text-slate-900 border-l-4 border-emerald-600"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 border-l-4 border-transparent"
            )}
          >
            <span className={!activeTaskId ? "text-emerald-600" : "text-slate-400"}>
              <BarChart3 className="w-4 h-4" />
            </span>
            Dashboard
          </Link>
        </div>
      </div>

      {/* Autonomous vs Manual Action Tabs */}
      <div className="mb-6 px-2">
        <div className="flex border-b border-slate-200 mb-4 px-2">
          <button 
            className={cn(
              "flex-1 pb-2 text-xs font-bold uppercase tracking-wider text-center transition-colors border-b-2",
              activeTab === "upload" ? "border-blue-500 text-blue-600" : "border-transparent text-slate-400 hover:text-slate-600"
            )}
            onClick={() => setActiveTab("upload")}
          >
            Upload
          </button>
          <button 
            className={cn(
              "flex-1 pb-2 text-xs font-bold uppercase tracking-wider text-center transition-colors border-b-2",
              activeTab === "crawl" ? "border-blue-500 text-blue-600" : "border-transparent text-slate-400 hover:text-slate-600"
            )}
            onClick={() => setActiveTab("crawl")}
          >
            Bot Crawl
          </button>
        </div>

        {activeTab === "upload" ? (
          <div className="px-2">
            <input 
              type="file" 
              accept="video/*" 
              className="hidden" 
              ref={fileInputRef}
              onChange={handleFileUpload}
            />
            <Button 
              variant="outline" 
              className="w-full justify-start text-slate-600 border border-slate-200 hover:bg-slate-50 transition-colors h-10 rounded-md font-medium"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              {isUploading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <UploadCloud className="w-4 h-4 mr-2" />
              )}
              {isUploading ? "Uploading..." : "Upload New Video"}
            </Button>
            
            {isUploading && (
              <div className="mt-3 px-1">
                <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-1">
                  <span>Upload</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 rounded-full transition-all duration-300" 
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
            <p className="text-[10px] text-slate-400 mt-2 text-center">
              MP4, MOV, AVI, WEBM (Max 200MB)
            </p>
          </div>
        ) : (
          <div className="px-2 flex flex-col gap-3">
            <input 
              type="url" 
              value={crawlUrl}
              onChange={(e) => setCrawlUrl(e.target.value)}
              placeholder="https://betting-site.com"
              className="w-full border border-slate-200 rounded-md h-10 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={isCrawling}
            />
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider w-16">Duration</span>
              <input 
                type="range" 
                min="10" max="120" 
                value={crawlDuration} 
                onChange={(e) => setCrawlDuration(parseInt(e.target.value))}
                className="flex-1"
                disabled={isCrawling}
              />
              <span className="text-xs font-mono text-slate-600 w-8">{crawlDuration}s</span>
            </div>
            <Button 
              className="w-full justify-start bg-slate-900 text-white hover:bg-slate-800 transition-colors h-10 rounded-md font-medium"
              onClick={handleCrawlStart}
              disabled={isCrawling || !crawlUrl}
            >
              {isCrawling ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Bot className="w-4 h-4 mr-2" />
              )}
              {isCrawling ? "Crawling & Recording..." : "Start Autonomous Bot"}
            </Button>
          </div>
        )}
      </div>

      {/* Previous Analyses */}
      <div className="mb-6">
        <h3 className="px-4 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          Previous Analyses
        </h3>
        <div className="space-y-1 mt-2">
          {tasks.length === 0 ? (
            <p className="px-4 text-xs text-slate-400 italic">No analyses yet.</p>
          ) : (
            tasks.map((task) => {
              const isActive = activeTaskId === task.id.toString();
              return (
                <Link
                  key={task.id}
                  href={`/?task=${task.id}`}
                  className={cn(
                    "flex flex-col gap-1 px-3 py-2 rounded-md text-sm transition-colors",
                    isActive
                      ? "bg-slate-100 text-slate-900 font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  )}
                >
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2 truncate pr-2">
                      <Video className={cn("w-3.5 h-3.5 shrink-0", isActive ? "text-emerald-600" : "text-slate-400")} />
                      <span className="truncate">{task.video_name}</span>
                    </div>
                    {getStatusIcon(task.status)}
                  </div>
                  <div className="text-[10px] text-slate-400 flex justify-between pl-5">
                    <span>{task.id}</span>
                    {task.status === "processing" && (
                      <span className="text-blue-500 font-bold">{Math.round(task.progress * 100)}%</span>
                    )}
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </div>

    </div>
  );
}
