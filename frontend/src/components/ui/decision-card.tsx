import React from "react"
import { motion } from "framer-motion"

interface DecisionCardProps {
  label: string
  subtext: string
  icon: React.ReactNode
  onClick: () => void
  delay?: number
}

const DecisionCard: React.FC<DecisionCardProps> = ({
  label,
  subtext,
  icon,
  onClick,
  delay = 0,
}) => {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
      whileHover={{ 
        y: -5, 
        transition: { duration: 0.2 }
      }}
      onClick={onClick}
      className="group relative flex flex-col items-start gap-3 p-5 rounded-[24px] glass-dark border border-white/5 hover:border-primary/40 transition-all text-left w-full max-w-[280px] overflow-hidden"
    >
      {/* Glow Effect */}
      <div className="absolute -inset-1 bg-gradient-to-br from-primary/20 to-transparent opacity-0 group-hover:opacity-100 blur-xl transition-opacity pointer-events-none" />
      
      <div className="relative p-3 rounded-xl bg-white/[0.03] group-hover:bg-primary/10 border border-white/5 group-hover:border-primary/20 transition-colors">
        <div className="text-muted-foreground group-hover:text-primary transition-colors group-hover:scale-110 transform transition-transform duration-300">
          {icon}
        </div>
      </div>
      
      <div className="relative space-y-1">
        <h4 className="text-[15px] font-semibold text-white/90 group-hover:text-white">
          {label}
        </h4>
        <p className="text-[12px] text-muted-foreground/80 leading-snug">
          {subtext}
        </p>
      </div>

      <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all duration-300">
        <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(204,20,20,0.8)]" />
      </div>
    </motion.button>
  )
}

export default DecisionCard
