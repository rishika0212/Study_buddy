import React from "react"
import { CheckCircle2, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { motion, AnimatePresence } from "framer-motion"

interface StrongArea {
  name: string
  mastery_pct: number
  mastery_achieved: string
  parent_topic_id?: string
}

interface StrongAreasPanelProps {
  areas: StrongArea[]
  moreCount: number
  onChallengeTopic?: (topic: string) => void
}

const StrongAreasPanel: React.FC<StrongAreasPanelProps> = ({
  areas,
  moreCount,
  onChallengeTopic
}) => {
  const [showAll, setShowAll] = React.useState(false)
  
  const displayedAreas = showAll ? areas : areas.slice(0, 10)
  const hasMore = moreCount > 0 && !showAll

  if (areas.length === 0) {
    return (
      <section className="space-y-3 p-4 rounded-xl bg-gradient-to-br from-green-500/5 to-emerald-500/5 border border-green-500/10">
        <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-green-400/60 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5" />
          🟢 Strong Areas (0)
        </h4>
        <p className="text-[12px] text-white/60 italic px-1">
          Complete an assessment to discover your strengths
        </p>
      </section>
    )
  }

  return (
    <section className="space-y-3 p-4 rounded-xl bg-gradient-to-br from-green-500/5 to-emerald-500/5 border border-green-500/10">
      <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-green-400/60 flex items-center gap-2">
        <CheckCircle2 className="w-3.5 h-3.5" />
        🟢 Strong Areas ({areas.length})
      </h4>

      <AnimatePresence mode="wait">
        <div className="space-y-2">
          {displayedAreas.map((area, idx) => (
            <motion.div
              key={area.name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ delay: idx * 0.05 }}
              className="p-3 rounded-lg bg-white/5 border border-green-500/20 hover:border-green-500/40 hover:bg-white/8 transition-all group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-semibold text-white/90 truncate group-hover:text-white">
                    {area.name}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-emerald-400 to-green-500 transition-all duration-300"
                        style={{ width: `${area.mastery_pct}%` }}
                      />
                    </div>
                    <span className="text-[11px] text-emerald-400/80 font-medium whitespace-nowrap">
                      {area.mastery_pct}%
                    </span>
                  </div>
                  <p className="text-[10px] text-white/40 mt-1">
                    Mastery achieved: {area.mastery_achieved}
                  </p>
                </div>

                <Button
                  onClick={() => onChallengeTopic?.(area.name)}
                  className="h-8 px-2.5 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 hover:border-green-500/50 text-green-300 hover:text-green-200 text-[11px] font-semibold rounded-lg transition-all shrink-0"
                >
                  <TrendingUp className="w-3 h-3" />
                  Challenge
                </Button>
              </div>
            </motion.div>
          ))}

          {hasMore && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={() => setShowAll(true)}
              className="w-full p-2 text-[11px] text-white/50 hover:text-white/70 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 transition-all"
            >
              and {moreCount} more
            </motion.button>
          )}

          {showAll && moreCount > 0 && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={() => setShowAll(false)}
              className="w-full p-2 text-[11px] text-white/50 hover:text-white/70 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 transition-all"
            >
              Show less
            </motion.button>
          )}
        </div>
      </AnimatePresence>
    </section>
  )
}

export default StrongAreasPanel
