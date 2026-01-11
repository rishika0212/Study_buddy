import React, { useState, useRef, useEffect } from "react"
import MessageBubble from "./MessageBubble"
import type { Message } from "./MessageBubble"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ArrowUp, BookOpen, Command, Brain, Fingerprint, Zap } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import DecisionCard from "./ui/decision-card"
import BackgroundEffects from "./ui/background-effects"

interface ChatWindowProps {
  messages: Message[]
  onSendMessage: (text: string) => void
  isLoading: boolean
  profile: {
    knowledge_level: string
    known_concepts: string[]
    weak_areas: string[]
  }
  disabled?: boolean
  isAssessmentActive?: boolean
  onCancelAssessment?: () => void
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  onSendMessage,
  isLoading,
  profile,
  disabled = false,
  isAssessmentActive = false,
  onCancelAssessment
}) => {
  const [input, setInput] = useState("")
  const [placeholder, setPlaceholder] = useState("Execute command...")
  const [isFocused, setIsFocused] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const placeholders = [
      "Ask for a deeper dive...",
      "What should we master next?",
      "Issuing new objective...",
      "Type a topic to begin...",
      "Challenge my understanding..."
    ]
    const interval = setInterval(() => {
      setPlaceholder(placeholders[Math.floor(Math.random() * placeholders.length)])
    }, 8000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth"
      })
    }
  }, [messages, isLoading])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSendMessage(input)
      setInput("")
    }
  }

  const getTimeGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return "Good morning"
    if (hour < 18) return "Good afternoon"
    return "Good evening"
  }

  const lastTopic = profile.known_concepts[profile.known_concepts.length - 1]
  const focusTopic = profile.weak_areas[0]

  const suggestions = [
    { 
      label: lastTopic ? `Continue ${lastTopic}` : "Start Learning", 
      subtext: lastTopic ? "You were close to mastering this." : "Enter any topic you want to explore.",
      icon: <BookOpen className="w-5 h-5" /> 
    },
    { 
      label: focusTopic ? `Fix ${focusTopic}` : "Identify Gaps", 
      subtext: focusTopic ? "I remember you struggled with this." : "Let's find what you need to work on.",
      icon: <Fingerprint className="w-5 h-5" /> 
    },
    { 
      label: "Ask a Question", 
      subtext: "Clear your doubts on any concept.",
      icon: <Zap className="w-5 h-5" /> 
    }
  ]

  const getGreeting = () => {
    const timeGreeting = getTimeGreeting()
    const name = "Rishika" // Static for now as per requirements
    return `${timeGreeting}, ${name}.`
  }

  return (
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      <BackgroundEffects />
      
      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 pt-20 pb-40 space-y-12 scrollbar-hide relative z-10"
      >
        <AnimatePresence mode="wait">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center min-h-[70vh] max-w-4xl mx-auto"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 1, ease: [0.19, 1, 0.22, 1] }}
                className="text-center space-y-8"
              >
                <div className="space-y-4">
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass border border-white/5 text-[10px] uppercase tracking-[0.2em] text-primary/80 font-bold"
                  >
                    <Brain className="w-3 h-3" />
                    Neural Sync Active
                  </motion.div>
                  <h3 className="text-5xl font-bold tracking-tighter text-gradient pb-2">
                    {getGreeting()}
                  </h3>
                  <p className="text-muted-foreground text-lg max-w-md mx-auto leading-relaxed">
                    {lastTopic 
                      ? `I've prepared a path to continue our journey with ${lastTopic}.`
                      : "We haven't started learning yet. What would you like to explore?"}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
                  {suggestions.map((suggestion, i) => (
                    <DecisionCard
                      key={suggestion.label}
                      label={suggestion.label}
                      subtext={suggestion.subtext}
                      icon={suggestion.icon}
                      delay={0.4 + i * 0.1}
                      onClick={() => onSendMessage(suggestion.label)}
                    />
                  ))}
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <div className="max-w-3xl mx-auto w-full space-y-10">
              {messages.map((msg) => (
                <div key={msg.id} className="space-y-4">
                  <MessageBubble message={msg} />
                </div>
              ))}
            </div>
          )}
        </AnimatePresence>

        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start max-w-3xl mx-auto"
          >
            <div className="glass px-6 py-4 rounded-2xl flex items-center gap-4">
              <div className="flex gap-1.5">
                <motion.div
                  animate={{ opacity: [0.3, 1, 0.3], scale: [1, 1.2, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="w-1.5 h-1.5 bg-primary rounded-full shadow-[0_0_8px_rgba(204,20,20,0.6)]"
                />
                <motion.div
                  animate={{ opacity: [0.3, 1, 0.3], scale: [1, 1.2, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }}
                  className="w-1.5 h-1.5 bg-primary rounded-full shadow-[0_0_8px_rgba(204,20,20,0.6)]"
                />
                <motion.div
                  animate={{ opacity: [0.3, 1, 0.3], scale: [1, 1.2, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }}
                  className="w-1.5 h-1.5 bg-primary rounded-full shadow-[0_0_8px_rgba(204,20,20,0.6)]"
                />
              </div>
              <span className="text-[11px] uppercase tracking-widest text-muted-foreground font-bold">
                Synthesizing response
              </span>
            </div>
          </motion.div>
        )}
      </div>

      {/* AI Command Console */}
      <div className="absolute bottom-0 left-0 right-0 p-10 z-20">
        <div className="max-w-3xl mx-auto relative group">
          {/* Brighter background glow for visibility */}
          <div className="absolute -inset-4 bg-primary/10 blur-3xl opacity-70 pointer-events-none" />
          
          <motion.div
            animate={isFocused ? { scale: 1.01 } : { scale: 1 }}
            className={`relative flex items-center bg-[#1a1a1e] backdrop-blur-3xl rounded-[28px] p-2 pl-7 shadow-[0_20px_50px_-10px_rgba(0,0,0,1)] transition-all duration-500 border-2 ${isFocused ? 'border-primary shadow-[0_0_30px_-5px_rgba(204,20,20,0.4)]' : 'border-white/20 hover:border-white/40'}`}
          >
            <Command className={`w-4 h-4 mr-4 transition-colors ${isFocused ? 'text-primary' : 'text-white/60'}`} />
            <form
              onSubmit={handleSubmit}
              className="flex-1 flex items-center"
            >
              <Input
                value={input}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isAssessmentActive ? "Provide your answer..." : placeholder}
                className="flex-1 bg-transparent border-none focus-visible:ring-0 text-white placeholder:text-white/40 py-8 text-[16px] tracking-tight font-medium transition-all"
                disabled={isLoading || disabled}
              />
              {isAssessmentActive && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={onCancelAssessment}
                  className="mr-2 text-[10px] text-destructive hover:bg-destructive/10 uppercase tracking-widest font-bold h-10 px-3 rounded-xl"
                >
                  Quit
                </Button>
              )}
              <motion.div
                animate={input.trim() && !disabled ? { scale: 1, opacity: 1 } : { scale: 0.8, opacity: 0 }}
              >
                <Button
                  type="submit"
                  disabled={isLoading || !input.trim() || disabled}
                  size="icon"
                  className="rounded-full w-12 h-12 bg-primary hover:bg-primary/90 text-white shrink-0 ml-2 shadow-[0_0_20px_rgba(204,20,20,0.3)] transition-all active:scale-95"
                >
                  <ArrowUp className="w-5 h-5" />
                </Button>
              </motion.div>
            </form>

            {/* Glowing Pulse Effect */}
            <AnimatePresence>
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 rounded-[28px] border-2 border-primary/30 animate-pulse-red pointer-events-none"
                />
              )}
            </AnimatePresence>
          </motion.div>
          
          <div className="flex justify-between items-center mt-5 px-6">
            <div className="flex items-center gap-4">
              <span className="text-[10px] text-muted-foreground/40 font-bold uppercase tracking-widest flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-primary/40" />
                Memory Persistent
              </span>
              <span className="text-[10px] text-muted-foreground/40 font-bold uppercase tracking-widest flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-primary/40" />
                Adaptive Learning
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground/20 font-mono">
              SYSTEM_CORE_v1.0.4
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatWindow
