"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Video, BarChart2, Clock, Target, CreditCard, Search, FileText } from "lucide-react";

import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";
import { OverviewTab } from "./tabs/OverviewTab";
import { TimelineTab } from "./tabs/TimelineTab";
import { BettingTab } from "./tabs/BettingTab";
import { TransactionsTab } from "./tabs/TransactionsTab";
import { SegmentExplorerTab } from "./tabs/SegmentExplorerTab";
import { ReportsTab } from "./tabs/ReportsTab";

export default function DashboardView() {
  const searchParams = useSearchParams();
  const taskId = searchParams.get("task");
  
  const [taskData, setTaskData] = useState<any>(null);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!taskId) return;
    
    let interval: NodeJS.Timeout;
    const loadData = async () => {
      try {
        const taskRes = await axios.get(`/api/status/${taskId}`);
        setTaskData(taskRes.data);
        
        if (taskRes.data.status === "complete") {
          const summaryRes = await axios.get(`/api/analyses/${taskId}/summary`);
          setSummaryData(summaryRes.data);
        } else {
          setSummaryData(null);
        }
      } catch (err) {
        console.error(err);
      }
    };

    setIsLoading(true);
    loadData().finally(() => setIsLoading(false));
    
    interval = setInterval(() => {
      if (taskData?.status !== "complete") {
        loadData();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId, taskData?.status]);

  const metrics = useDashboardMetrics(summaryData);

  if (!taskId) {
    return (
      <div className="flex flex-col items-center justify-center h-[75vh] text-center animate-in fade-in zoom-in duration-500">
        <div className="w-24 h-24 bg-gradient-to-tr from-slate-100 to-slate-50 rounded-full shadow-sm border border-slate-200 flex items-center justify-center mb-8">
          <Video className="w-10 h-10 text-slate-400" strokeWidth={1.5} />
        </div>
        <h2 className="text-2xl font-[800] text-slate-800 tracking-tight">No Analysis Selected</h2>
        <p className="text-slate-500 mt-3 max-w-md text-sm leading-relaxed">
          Upload a new video from the sidebar or input a URL to launch the autonomous bot. Your forensic dashboard will automatically generate upon completion.
        </p>
      </div>
    );
  }

  if (isLoading && !taskData) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  const isProcessing = taskData?.status === "processing";

  return (
    <div className="space-y-6 pb-20 font-sans">
      <div className="mb-6">
        <div className="flex items-baseline gap-3 mb-1">
          <span className="font-['Inter'] font-extrabold text-[1.8rem] text-[#1E293B]">
            Video Analysis
          </span>
          <span className="font-['JetBrains_Mono'] text-[0.7rem] text-[#0891B2] bg-[#E0F2FE] px-3 py-1 rounded-[20px] border border-[#BAE6FD] font-semibold">
            {taskData?.id || "unknown_task"}
          </span>
          {isProcessing && (
             <span className="font-['JetBrains_Mono'] text-[0.7rem] text-blue-700 bg-blue-100 px-3 py-1 rounded-[20px] border border-blue-200 font-semibold animate-pulse">
               Processing {Math.round((taskData.progress || 0) * 100)}%
             </span>
          )}
        </div>
        
        {!isProcessing && metrics && (
          <div className="text-[#64748B] font-['JetBrains_Mono'] text-[0.7rem] mb-6">
            <span className="text-[#1E293B] font-bold">{taskData?.original_filename || "Unknown File"}</span>
            <span>:Videoname</span> · {metrics.segmentCount} segments · {metrics.totalDuration.toFixed(1)}s total · {metrics.qrSegments.length} QR detections · {metrics.failedTxTimes.length} failed transactions
          </div>
        )}

        {isProcessing && (
          <div className="mt-4 max-w-md">
            <div className="flex justify-between text-xs font-bold text-slate-500 uppercase mb-1">
              <span>Extraction Progress</span>
              <span>{Math.round((taskData.progress || 0) * 100)}%</span>
            </div>
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out" 
                style={{ width: `${Math.round((taskData.progress || 0) * 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {!isProcessing && metrics && (
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="w-full flex justify-start bg-transparent border-b border-slate-200 p-0 h-10 mb-6 overflow-x-auto gap-4">
            <TabsTrigger value="overview" className="data-[state=active]:bg-transparent data-[state=active]:border-slate-800 data-[state=active]:text-slate-900 data-[state=active]:shadow-none border-b-2 border-transparent rounded-none h-full px-1 flex items-center gap-2 font-medium text-slate-500 hover:text-slate-700">
              Overview
            </TabsTrigger>
            <TabsTrigger value="timeline" className="data-[state=active]:bg-transparent data-[state=active]:border-slate-800 data-[state=active]:text-slate-900 data-[state=active]:shadow-none border-b-2 border-transparent rounded-none h-full px-1 flex items-center gap-2 font-medium text-slate-500 hover:text-slate-700">
              Timeline
            </TabsTrigger>
            <TabsTrigger value="betting" className="data-[state=active]:bg-transparent data-[state=active]:border-slate-800 data-[state=active]:text-slate-900 data-[state=active]:shadow-none border-b-2 border-transparent rounded-none h-full px-1 flex items-center gap-2 font-medium text-slate-500 hover:text-slate-700">
              Betting Analysis
            </TabsTrigger>
            <TabsTrigger value="transactions" className="data-[state=active]:bg-transparent data-[state=active]:border-slate-800 data-[state=active]:text-slate-900 data-[state=active]:shadow-none border-b-2 border-transparent rounded-none h-full px-1 flex items-center gap-2 font-medium text-slate-500 hover:text-slate-700">
              Transactions
            </TabsTrigger>
            <TabsTrigger value="explorer" className="data-[state=active]:bg-transparent data-[state=active]:border-slate-800 data-[state=active]:text-slate-900 data-[state=active]:shadow-none border-b-2 border-transparent rounded-none h-full px-1 flex items-center gap-2 font-medium text-slate-500 hover:text-slate-700">
              Segment Explorer
            </TabsTrigger>
            <TabsTrigger value="reports" className="data-[state=active]:bg-transparent data-[state=active]:border-slate-800 data-[state=active]:text-slate-900 data-[state=active]:shadow-none border-b-2 border-transparent rounded-none h-full px-1 flex items-center gap-2 font-medium text-slate-500 hover:text-slate-700">
              Reports
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab metrics={metrics} summaryData={summaryData} />
          </TabsContent>
          <TabsContent value="timeline">
            <TimelineTab metrics={metrics} summaryData={summaryData} />
          </TabsContent>
          <TabsContent value="betting">
            <BettingTab metrics={metrics} />
          </TabsContent>
          <TabsContent value="transactions">
            <TransactionsTab metrics={metrics} />
          </TabsContent>
          <TabsContent value="explorer">
            <SegmentExplorerTab metrics={metrics} summaryData={summaryData} />
          </TabsContent>
          <TabsContent value="reports">
            <ReportsTab summaryData={summaryData} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
