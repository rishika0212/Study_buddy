import React from "react"
import { cn } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import { motion } from "framer-motion"
import { Brain, Sparkles, CheckCircle2, ClipboardCheck, LayoutList } from "lucide-react"

export interface Message {
  id: string
  text: string
  sender: "user" | "ai"
  timestamp: Date
  metadata?: {
    observation?: {
      intent: string
      confidence_level: number
      confusion_detected: boolean
    }
    plan?: {
      strategy: string
      depth: string
      focus_area: string
      reasoning: string
    }
    reflection?: {
      effectiveness: number
      user_progress: string
    }
    evaluation?: {
      is_correct?: boolean
      total_marks?: number
      marks?: number
      feedback?: string
    }
    assessment_completed?: boolean
  }
}

interface MessageBubbleProps {
  message: Message
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isAI = message.sender === "ai"

  const getConfidenceLabel = () => {
    const confidence = message.metadata?.observation?.confidence_level || 0.8
    if (confidence > 0.9) return "Highly Certain"
    if (confidence > 0.7) return "Confident"
    return "Exploring Patterns"
  }

  const getDepthLabel = () => {
    const depth = message.metadata?.plan?.depth || "normal"
    if (depth === "beginner") return "Explained Simply"
    if (depth === "advanced") return "Going Deeper"
    return "Standard Analysis"
  }

  const renderAssessment = () => {
    if (!message.text.includes("QUIZ_MCQ_SESSION:") && !message.text.includes("QUIZ_QNA_SESSION:")) return null;

    const isMCQ = message.text.includes("QUIZ_MCQ_SESSION:");
    const marker = isMCQ ? "QUIZ_MCQ_SESSION: " : "QUIZ_QNA_SESSION: ";
    
    try {
      const parts = message.text.split(marker);
      const jsonPart = parts[1].split("\n\n")[0];
      const data = JSON.parse(jsonPart);

      return (
        <div className="mb-6 p-4 rounded-xl bg-primary/5 border border-primary/20 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/20">
                {isMCQ ? <LayoutList className="w-4 h-4 text-primary" /> : <ClipboardCheck className="w-4 h-4 text-primary" />}
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-primary/70">
                  {isMCQ ? "MCQ Assessment" : "Q&A Assessment"}
                </p>
                <p className="text-xs font-semibold text-white/90">{data.topic}</p>
              </div>
            </div>
            {isMCQ && (
              <div className="text-right">
                <p className="text-[10px] font-bold text-muted-foreground/60 uppercase">Progress</p>
                <p className="text-xs font-mono text-primary">{data.current_index + 1} / {data.total}</p>
              </div>
            )}
          </div>
          <div className="h-[1px] bg-white/5 w-full" />
        </div>
      );
    } catch (e) {
      console.error("Failed to parse assessment data", e);
      return null;
    }
  };

  const cleanText = (text: string) => {
    if (text.includes("QUIZ_MCQ_SESSION:")) {
      return text.split("\n\n").slice(1).join("\n\n");
    }
    if (text.includes("QUIZ_QNA_SESSION:")) {
      return text.split("\n\n").slice(1).join("\n\n");
    }
    return text;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex w-full",
        isAI ? "justify-start" : "justify-end"
      )}
    >
      <div className={cn("max-w-[85%] space-y-3", isAI ? "w-full" : "w-auto")}>
        {isAI ? (
          <div className="space-y-4 w-full">
            {/* Memory Recall Banner */}
            {message.metadata?.plan?.reasoning && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/5 border border-primary/10 w-fit"
              >
                <Brain className="w-3 h-3 text-primary/60" />
                <span className="text-[10px] text-primary/70 font-semibold uppercase tracking-widest">
                  Memory Recall: {message.metadata.plan.reasoning.split('.')[0]}
                </span>
              </motion.div>
            )}

            <Card className="premium-card p-6 relative overflow-hidden group border-white/5">
              <div className="absolute top-0 left-0 w-1 h-full bg-primary/30 group-hover:bg-primary transition-colors" />
              <div className="relative z-10 space-y-4">
                {message.metadata?.evaluation && (
                  <div className={cn(
                    "flex items-center gap-3 p-3 rounded-xl border mb-2",
                    message.metadata.evaluation.is_correct === false || (message.metadata.evaluation.total_marks !== undefined && message.metadata.evaluation.total_marks < 5)
                      ? "bg-destructive/10 border-destructive/20 text-destructive-foreground"
                      : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500"
                  )}>
                    <CheckCircle2 className="w-5 h-5 shrink-0" />
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wider">
                        Evaluation Results: {message.metadata.evaluation.total_marks !== undefined ? `${message.metadata.evaluation.total_marks}/10` : (message.metadata.evaluation.is_correct ? "Correct" : "Incorrect")}
                      </p>
                    </div>
                  </div>
                )}
                {renderAssessment()}
                <p className="text-[16px] leading-relaxed text-white/90 whitespace-pre-wrap">
                  {cleanText(message.text)}
                </p>
              </div>

              {/* Confidence Indicator */}
              <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500/60" />
                    <span className="text-[10px] text-muted-foreground/60 font-bold uppercase tracking-tight">
                      {getConfidenceLabel()}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-primary/60" />
                    <span className="text-[10px] text-muted-foreground/60 font-bold uppercase tracking-tight">
                      {getDepthLabel()}
                    </span>
                  </div>
                </div>
                {message.metadata?.plan?.focus_area && (
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/5 border border-white/5">
                    <span className="text-[9px] text-muted-foreground/40 font-bold uppercase">
                      Target: {message.metadata.plan.focus_area}
                    </span>
                  </div>
                )}
              </div>
            </Card>
          </div>
        ) : (
          <div className="flex flex-col items-end gap-2">
            <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-[22px] rounded-tr-none px-6 py-3.5 text-white/90 text-[15px] shadow-xl">
              {message.text}
            </div>
            <div className="flex items-center gap-1 px-2">
              <span className="text-[9px] text-muted-foreground/30 font-bold uppercase tracking-widest">
                Authorized Input
              </span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default MessageBubble
