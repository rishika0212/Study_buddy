import React from "react"
import { motion } from "framer-motion"

interface CircularProgressProps {
  progress: number
  size?: number
  strokeWidth?: number
  className?: string
  glow?: boolean
}

const CircularProgress: React.FC<CircularProgressProps> = ({
  progress,
  size = 120,
  strokeWidth = 8,
  className = "",
  glow = true,
}) => {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (progress / 100) * circumference

  return (
    <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          className="text-white/[0.03]"
        />
        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeInOut" }}
          strokeLinecap="round"
          className="text-primary"
          style={{
            filter: glow ? "drop-shadow(0 0 8px rgba(204, 20, 20, 0.4))" : "none",
          }}
        />
      </svg>
      {/* Content in the middle */}
      <div className="absolute flex flex-col items-center justify-center text-center">
        <motion.span 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-2xl font-bold text-white tracking-tighter"
        >
          {progress}%
        </motion.span>
        <span className="text-[9px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
          Mastery
        </span>
      </div>
    </div>
  )
}

export default CircularProgress
