import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ArrowLeft, ArrowRight, Download, AlertTriangle } from "lucide-react";

// Categorization Logic Ported from Python
const CATEGORIZED_KEYWORDS: Record<string, string[]> = {
  "Financial / Banking": ["deposit", "withdraw", "withdrawal", "wallet", "cashier", "payment", "pay", "transactions", "transaction", "recharge", "upi", "bank"],
  "Incentives / Promos": ["bonus", "referral", "rewards", "reward"],
  "Authentication / PII": ["kyc", "profile", "account", "login", "log in", "sign in", "signin", "register", "sign up", "signup", "phone number", "phone", "mobile", "mobile number", "email", "e-mail"],
  "Gaming / Betting": ["bet", "casino", "spin", "play", "win", "jackpot", "odds", "dealer"],
  "Crypto": ["usdt", "btc", "eth", "crypto", "bitcoin", "ethereum", "wallet address"],
};

function getDetectedCategories(ocrText: string) {
  const text = ocrText.toLowerCase();
  const detected: Record<string, string[]> = {};
  for (const [category, keywords] of Object.entries(CATEGORIZED_KEYWORDS)) {
    for (const kw of keywords) {
      if (text.includes(kw.toLowerCase())) {
        if (!detected[category]) detected[category] = [];
        if (!detected[category].includes(kw)) detected[category].push(kw);
      }
    }
  }
  return detected;
}

export function SegmentExplorerTab({ metrics, summaryData }: { metrics: any, summaryData: any }) {
  const [segIdx, setSegIdx] = useState(0);

  if (!metrics || !summaryData) return null;
  const verdicts = metrics.verdicts;

  if (verdicts.length === 0) return null;
  const seg = verdicts[segIdx];

  const downloadPdf = async () => {
    try {
        const response = await fetch(`/api/generate-pdf/${seg.segment_index}`);
        if(response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `segment_${seg.segment_index}_report.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } else {
            alert('PDF Generation not fully implemented yet');
        }
    } catch (error) {
        console.error(error);
        alert('Failed to generate PDF');
    }
  }

  return (
    <div className="space-y-6">
      {/* Segment Controls */}
      <div className="flex items-center justify-between bg-white p-4 rounded-lg border shadow-sm">
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            onClick={() => setSegIdx(Math.max(0, segIdx - 1))}
            disabled={segIdx === 0}
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Previous
          </Button>
          
          <select 
            className="h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
            value={segIdx}
            onChange={(e) => setSegIdx(Number(e.target.value))}
          >
            {verdicts.map((v: any, i: number) => (
              <option key={v.id || i} value={i}>
                Seg {(i + 1).toString().padStart(3, '0')} | {(v.start_time || 0).toFixed(2)}s - {(v.end_time || 0).toFixed(2)}s
              </option>
            ))}
          </select>

          <Button 
            variant="outline"
            onClick={() => setSegIdx(Math.min(verdicts.length - 1, segIdx + 1))}
            disabled={segIdx === verdicts.length - 1}
          >
            Next <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
        
        <Button variant="default" className="bg-red-500 hover:bg-red-600 text-white" onClick={downloadPdf}>
          <Download className="w-4 h-4 mr-2" /> Master PDF (All Segments)
        </Button>
      </div>

      {/* Segment Details */}
      {seg && (
        <div className="grid grid-cols-1 gap-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="shadow-sm border-slate-200">
              <CardHeader>
                <CardTitle className="text-xs font-bold text-slate-500 uppercase tracking-wider">Classification Engine</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <MetricBar label="Banking Context" score={seg.banking_context} colorClass="bg-cyan-500" />
                <MetricBar label="Crypto Context" score={seg.crypto_context} colorClass="bg-purple-500" />
                <MetricBar label="Transaction Likely" score={seg.transaction_likely} colorClass="bg-red-500" />
                <MetricBar label="Tx Executed" score={seg.transaction_executed || 0} colorClass="bg-emerald-500" />
                <MetricBar label="Betting Score" score={metrics.betScores[segIdx] || 0} colorClass="bg-amber-500" />
              </CardContent>
            </Card>

            <Card className="shadow-sm border-slate-200">
              <CardHeader>
                <CardTitle className="text-xs font-bold text-slate-500 uppercase tracking-wider">Video Playback Sync</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-900 rounded-lg aspect-video flex items-center justify-center relative overflow-hidden group">
                    <video 
                      className="w-full h-full object-contain" 
                      controls 
                      key={summaryData.original_filename}
                      src={`/uploads/${summaryData.original_filename}#t=${seg.start_time}`}
                    />
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="shadow-sm border-slate-200 overflow-hidden">
            <CardHeader className="bg-slate-50 border-b border-slate-100">
              <CardTitle className="text-xs font-bold text-slate-500 uppercase tracking-wider">Forensic Proof Frame</CardTitle>
            </CardHeader>
            <div className="bg-slate-900 p-2 flex justify-center">
              <img 
                src={`/${seg.proof_frame}`} 
                alt="Proof Frame" 
                className="max-h-[600px] object-contain shadow-2xl rounded-sm"
              />
            </div>
            <CardContent className="p-6">
              <h4 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" /> Detected Categories in OCR
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(getDetectedCategories(seg.ocr_text || "")).map(([cat, words]) => (
                  <Badge key={cat} variant="outline" className="text-xs py-1 px-3 border-emerald-200 bg-emerald-50 text-emerald-800">
                    <span className="font-bold mr-1">{cat}:</span> {words.join(", ")}
                  </Badge>
                ))}
                {Object.keys(getDetectedCategories(seg.ocr_text || "")).length === 0 && (
                  <span className="text-sm text-slate-400 italic">No categorized keywords specifically tagged in this view.</span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function MetricBar({ label, score, colorClass }: { label: string, score: number, colorClass: string }) {
  const safeScore = score || 0;
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs font-bold text-slate-700">
        <span>{label}</span>
        <span>{safeScore.toFixed(1)}%</span>
      </div>
      <Progress value={safeScore} className={cn("h-2.5 bg-slate-100", `[&>div]:${colorClass}`)} />
    </div>
  );
}
