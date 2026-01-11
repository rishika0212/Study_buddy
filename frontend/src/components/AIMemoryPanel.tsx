import React from "react"
import { Trash2, GraduationCap, Zap, ClipboardCheck, LayoutList, MessageSquareText, X, Hash, ChevronDown, ChevronRight, BookOpen, AlertTriangle, Star, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { motion, AnimatePresence } from "framer-motion"
import CircularProgress from "./ui/circular-progress"

interface TopicData {
  name: string
  mastery_score: number
  questions_attempted: number
  correct_answers: number
  classification: string
  explanation_summary: string
}

interface AIMemoryPanelProps {
  level: string
  concepts: string[]
  weakAreas: string[]
  allTopics: TopicData[]
  weakTopics: TopicData[]
  strongTopics: TopicData[]
  overallMastery: number  // 0-1, calculated dynamically from assessed topics only
  onReset: () => void
  onNewSession: () => void
  assessmentState: {
    step: 'idle' | 'scope' | 'count' | 'active'
    type: 'MCQ' | 'QNA' | null
    selectedTopics: string[]
    questionCount: number | null
  }
  onStartAssessment: (type: 'MCQ' | 'QNA') => void
  onToggleTopic: (topic: string) => void
  onSetQuestionCount: (count: number) => void
  onConfirmAssessment: () => void
  onCancelAssessment: () => void
  onPracticeTopic?: (topic: string) => void
  onChallengeTopic?: (topic: string) => void
}

const AIMemoryPanel: React.FC<AIMemoryPanelProps> = ({
  level: _level,
  concepts: _concepts,
  weakAreas: _weakAreas,
  allTopics = [],
  weakTopics = [],
  strongTopics = [],
  overallMastery = 0,
  onReset,
  onNewSession,
  assessmentState,
  onStartAssessment,
  onToggleTopic,
  onSetQuestionCount,
  onConfirmAssessment,
  onCancelAssessment,
  onPracticeTopic,
  onChallengeTopic
}) => {
  void _weakAreas
  void _level
  void _concepts
  
  const [expandedSections, setExpandedSections] = React.useState<{
    allTopics: boolean
    weakTopics: boolean
    strongTopics: boolean
    assessments: boolean
  }>({
    allTopics: true,
    weakTopics: false,
    strongTopics: false,
    assessments: true
  })

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const getProgress = () => {
    // Overall mastery is calculated dynamically from assessed topics only
    // Returns percentage (0-100) for CircularProgress
    return Math.round(overallMastery * 100)
  }

  const getMasteryLabel = () => {
    // Count assessed topics (questions_attempted > 0)
    const assessedCount = allTopics.filter(t => t.questions_attempted > 0).length
    if (assessedCount === 0) return "No assessments yet"
    const masteryPct = Math.round(overallMastery * 100)
    return `${masteryPct}% Overall Mastery`
  }

  const getMasteryColor = (score: number) => {
    // Classification threshold: >= 0.40 is strong, < 0.40 is weak
    if (score >= 0.40) return "text-emerald-400"
    return "text-red-400"
  }

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case "strong":
        return <span className="px-1.5 py-0.5 rounded text-[8px] bg-emerald-500/20 text-emerald-400 uppercase">Strong</span>
      case "weak":
        return <span className="px-1.5 py-0.5 rounded text-[8px] bg-red-500/20 text-red-400 uppercase">Weak</span>
      default:
        return <span className="px-1.5 py-0.5 rounded text-[8px] bg-gray-500/20 text-gray-400 uppercase">Unassessed</span>
    }
  }

  const assessmentTopics = allTopics.map(t => t.name)

  return (
    <div className="flex flex-col h-full bg-transparent overflow-hidden">
      {/* Brand Section */}
      <div className="flex items-center gap-3 mb-8 group cursor-default">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full group-hover:bg-primary/40 transition-all duration-500" />
          <div className="relative p-2.5 rounded-2xl glass-dark border border-white/10 group-hover:border-primary/50 transition-colors">
            <GraduationCap className="w-5 h-5 text-primary group-hover:scale-110 transition-transform" />
          </div>
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-white/90">
            Study Buddy
          </h1>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/80 animate-pulse" />
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
              Topic-Based Learning
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-4 pr-1">
        
        {/* All Topics Dropdown */}
        <section className="space-y-2">
          <button
            onClick={() => toggleSection('allTopics')}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
          >
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary" />
              <span className="text-xs font-semibold text-white/90">All Topics</span>
              <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-primary/20 text-primary">
                {allTopics.length}
              </span>
            </div>
            {expandedSections.allTopics ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          
          <AnimatePresence>
            {expandedSections.allTopics && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-1 pl-2"
              >
                {allTopics.length > 0 ? (
                  allTopics.map((topic) => (
                    <div
                      key={topic.name}
                      className="p-2 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-white/80 truncate flex-1">{topic.name}</span>
                        {getClassificationBadge(topic.classification)}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[9px] ${getMasteryColor(topic.mastery_score)}`}>
                          {Math.round(topic.mastery_score * 100)}% mastery
                        </span>
                        <span className="text-[9px] text-muted-foreground">
                          {topic.questions_attempted} Q
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-[10px] text-muted-foreground italic p-2">
                    No topics explained yet. Ask me to explain something!
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Weak Topics Dropdown */}
        <section className="space-y-2">
          <button
            onClick={() => toggleSection('weakTopics')}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-red-500/5 border border-red-500/20 hover:bg-red-500/10 transition-all"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-xs font-semibold text-white/90">Weak Topics</span>
              <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-red-500/20 text-red-400">
                {weakTopics.length}
              </span>
            </div>
            {expandedSections.weakTopics ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          
          <AnimatePresence>
            {expandedSections.weakTopics && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-1 pl-2"
              >
                {weakTopics.length > 0 ? (
                  weakTopics.map((topic) => (
                    <div
                      key={topic.name}
                      className="p-2 rounded-lg bg-red-500/5 border border-red-500/10 hover:border-red-500/20 transition-all group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-white/80 truncate flex-1">{topic.name}</span>
                        <span className="text-[9px] text-red-400">
                          {Math.round(topic.mastery_score * 100)}%
                        </span>
                      </div>
                      {onPracticeTopic && (
                        <button
                          onClick={() => onPracticeTopic(topic.name)}
                          className="mt-1 text-[9px] text-red-400 hover:text-red-300 transition-colors"
                        >
                          Practice this topic →
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-[10px] text-muted-foreground italic p-2">
                    No weak topics. Keep up the great work!
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Strong Topics Dropdown */}
        <section className="space-y-2">
          <button
            onClick={() => toggleSection('strongTopics')}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20 hover:bg-emerald-500/10 transition-all"
          >
            <div className="flex items-center gap-2">
              <Star className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-white/90">Strong Topics</span>
              <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-emerald-500/20 text-emerald-400">
                {strongTopics.length}
              </span>
            </div>
            {expandedSections.strongTopics ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          
          <AnimatePresence>
            {expandedSections.strongTopics && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-1 pl-2"
              >
                {strongTopics.length > 0 ? (
                  strongTopics.map((topic) => (
                    <div
                      key={topic.name}
                      className="p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10 hover:border-emerald-500/20 transition-all group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-white/80 truncate flex-1">{topic.name}</span>
                        <span className="text-[9px] text-emerald-400">
                          {Math.round(topic.mastery_score * 100)}%
                        </span>
                      </div>
                      {onChallengeTopic && (
                        <button
                          onClick={() => onChallengeTopic(topic.name)}
                          className="mt-1 text-[9px] text-emerald-400 hover:text-emerald-300 transition-colors"
                        >
                          Challenge yourself →
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-[10px] text-muted-foreground italic p-2">
                    Complete assessments to build strong topics!
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Assessments Dropdown */}
        <section className="space-y-2">
          <button
            onClick={() => toggleSection('assessments')}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-primary/5 border border-primary/20 hover:bg-primary/10 transition-all"
          >
            <div className="flex items-center gap-2">
              <ClipboardCheck className="w-4 h-4 text-primary" />
              <span className="text-xs font-semibold text-white/90">Assessments</span>
            </div>
            {expandedSections.assessments ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          
          <AnimatePresence>
            {expandedSections.assessments && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-2 pl-2"
              >
                <AnimatePresence mode="wait">
                  {assessmentState.step === 'idle' && (
                    <motion.div
                      key="idle"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="grid grid-cols-1 gap-2"
                    >
                      <Button
                        onClick={() => onStartAssessment('MCQ')}
                        disabled={assessmentTopics.length === 0}
                        className="w-full h-10 bg-white/5 hover:bg-primary/20 border border-white/5 hover:border-primary/40 text-white/90 justify-start px-4 gap-3 rounded-xl transition-all group disabled:opacity-50"
                      >
                        <LayoutList className="w-4 h-4 text-primary" />
                        <span className="text-xs font-semibold">Take MCQ</span>
                      </Button>
                      <Button
                        onClick={() => onStartAssessment('QNA')}
                        disabled={assessmentTopics.length === 0}
                        className="w-full h-10 bg-white/5 hover:bg-primary/20 border border-white/5 hover:border-primary/40 text-white/90 justify-start px-4 gap-3 rounded-xl transition-all group disabled:opacity-50"
                      >
                        <MessageSquareText className="w-4 h-4 text-primary" />
                        <span className="text-xs font-semibold">Take Q&A</span>
                      </Button>
                      {assessmentTopics.length === 0 && (
                        <p className="text-[9px] text-muted-foreground italic text-center">
                          Explain topics first to enable assessments
                        </p>
                      )}
                    </motion.div>
                  )}

                  {assessmentState.step === 'scope' && (
                    <motion.div
                      key="scope"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="space-y-3 p-3 rounded-xl bg-white/5 border border-white/10"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-bold uppercase text-primary">Step 1: Select Topics</span>
                        <button onClick={onCancelAssessment} className="text-muted-foreground hover:text-white">
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                      <p className="text-[10px] text-white/70">Choose topics for {assessmentState.type}:</p>
                      <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                        {assessmentTopics.length > 0 ? (
                          assessmentTopics.map(topic => (
                            <button
                              key={topic}
                              onClick={() => onToggleTopic(topic)}
                              className={`px-2 py-1 rounded-md text-[10px] border transition-all ${
                                assessmentState.selectedTopics.includes(topic)
                                  ? "bg-primary/20 border-primary/40 text-white"
                                  : "bg-black/20 border-white/5 text-white/40"
                              }`}
                            >
                              {topic}
                            </button>
                          ))
                        ) : (
                          <p className="text-[10px] text-muted-foreground italic">
                            No topics available. Explain topics first.
                          </p>
                        )}
                      </div>
                      <Button 
                        onClick={() => onSetQuestionCount(0)}
                        disabled={assessmentState.selectedTopics.length === 0}
                        className="w-full h-8 bg-primary text-white text-[10px] font-bold uppercase tracking-widest"
                      >
                        Confirm Topics
                      </Button>
                    </motion.div>
                  )}

                  {assessmentState.step === 'count' && (
                    <motion.div
                      key="count"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="space-y-3 p-3 rounded-xl bg-white/5 border border-white/10"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-bold uppercase text-primary">Step 2: Question Count</span>
                        <button onClick={onCancelAssessment} className="text-muted-foreground hover:text-white">
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                      
                      <div className="space-y-2">
                        <label className="text-[9px] text-muted-foreground uppercase tracking-widest px-1">Enter count (1-50)</label>
                        <div className="relative">
                          <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-primary/50" />
                          <Input
                            type="number"
                            min={1}
                            max={50}
                            placeholder="Enter count..."
                            value={assessmentState.questionCount || ""}
                            onChange={(e) => {
                              const val = e.target.value;
                              if (val === "") {
                                onSetQuestionCount(0);
                                return;
                              }
                              const num = parseInt(val);
                              if (!isNaN(num)) {
                                onSetQuestionCount(num);
                              }
                            }}
                            className="bg-black/20 border-white/5 h-9 pl-9 text-xs focus:ring-primary/20"
                          />
                        </div>
                      </div>

                      <Button 
                        onClick={onConfirmAssessment}
                        disabled={!assessmentState.questionCount || assessmentState.questionCount < 1 || assessmentState.questionCount > 50}
                        className="w-full h-8 bg-primary text-white text-[10px] font-bold uppercase tracking-widest"
                      >
                        Start Assessment
                      </Button>
                    </motion.div>
                  )}

                  {assessmentState.step === 'active' && (
                    <motion.div
                      key="active"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="p-3 rounded-xl bg-primary/10 border border-primary/30 text-center space-y-2"
                    >
                      <div className="flex justify-center">
                        <div className="p-2 rounded-full bg-primary/20 animate-pulse">
                          <ClipboardCheck className="w-5 h-5 text-primary" />
                        </div>
                      </div>
                      <p className="text-xs font-bold text-white uppercase tracking-wider">Assessment Active</p>
                      <p className="text-[10px] text-primary/70">Answer questions in the chat</p>
                      <Button 
                        variant="ghost" 
                        onClick={onCancelAssessment}
                        className="text-[10px] h-7 text-destructive hover:bg-destructive/10"
                      >
                        Cancel
                      </Button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Progress Section */}
        <section className="space-y-4 pt-4">
          <div className="flex flex-col items-center justify-center p-4">
            <CircularProgress progress={getProgress()} size={120} strokeWidth={8} />
            <div className="mt-3 text-center">
              <p className="text-xs font-medium text-primary/80 tracking-wide flex items-center gap-2 justify-center">
                <Zap className="w-3 h-3" />
                {allTopics.length} topics learned
              </p>
              <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-tighter">
                {getMasteryLabel()}
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <div className="mt-auto pt-4 border-t border-white/5 space-y-2">
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground/70 hover:text-primary hover:bg-primary/5 text-[10px] h-9 gap-2 px-2 transition-all group"
          onClick={onNewSession}
        >
          <RefreshCw className="w-3.5 h-3.5 group-hover:rotate-180 transition-transform duration-500" />
          New Session
        </Button>
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground/30 hover:text-destructive hover:bg-destructive/5 text-[10px] h-9 gap-2 px-2 transition-all group"
          onClick={onReset}
        >
          <Trash2 className="w-3.5 h-3.5 group-hover:rotate-12 transition-transform" />
          Reset All Progress
        </Button>
      </div>
    </div>
  )
}

export default AIMemoryPanel
