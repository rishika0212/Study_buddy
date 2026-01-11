import React from "react"
import { ClipboardCheck, LayoutList, MessageSquareText } from "lucide-react"
import { Button } from "@/components/ui/button"

interface AssessmentPanelProps {
  onStartMCQ: () => void
  onStartQnA: () => void
  disabled?: boolean
}

const AssessmentPanel: React.FC<AssessmentPanelProps> = ({
  onStartMCQ,
  onStartQnA,
  disabled = false
}) => {
  return (
    <div className="space-y-6">
      <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 flex items-center gap-2 px-1">
        <ClipboardCheck className="w-3 h-3" />
        Take Assessment
      </h4>
      <div className="grid grid-cols-1 gap-3 px-1">
        <Button
          onClick={onStartMCQ}
          disabled={disabled}
          className="h-14 bg-white/5 hover:bg-white/10 border border-white/5 hover:border-primary/30 text-white/90 justify-start px-4 gap-4 rounded-xl transition-all group"
        >
          <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
            <LayoutList className="w-4 h-4 text-primary" />
          </div>
          <div className="flex flex-col items-start">
            <span className="text-sm font-semibold">MCQ</span>
            <span className="text-[10px] text-muted-foreground">Multiple Choice Questions</span>
          </div>
        </Button>

        <Button
          onClick={onStartQnA}
          disabled={disabled}
          className="h-14 bg-white/5 hover:bg-white/10 border border-white/5 hover:border-primary/30 text-white/90 justify-start px-4 gap-4 rounded-xl transition-all group"
        >
          <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
            <MessageSquareText className="w-4 h-4 text-primary" />
          </div>
          <div className="flex flex-col items-start">
            <span className="text-sm font-semibold">Q&A</span>
            <span className="text-[10px] text-muted-foreground">Short & Long Answers</span>
          </div>
        </Button>
      </div>
    </div>
  )
}

export default AssessmentPanel
