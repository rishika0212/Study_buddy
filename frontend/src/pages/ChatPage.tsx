import React, { useEffect, useState } from "react"
import ChatWindow from "../components/ChatWindow"
import MCQAssessment from "../components/MCQAssessment"
import QnAAssessment from "../components/QnAAssessment"
import AIMemoryPanel from "../components/AIMemoryPanel"
import { useChat } from "../hooks/useChat"
import { chatApi } from "../services/api"
import { TooltipProvider } from "@/components/ui/tooltip"

interface TopicData {
  name: string
  mastery_score: number
  questions_attempted: number
  correct_answers: number
  classification: string
  explanation_summary: string
}

const ChatPage: React.FC = () => {
  const [userId] = useState(() => {
    const saved = localStorage.getItem("study_buddy_user_id")
    if (saved) return saved
    const newId = Math.random().toString(36).substring(7)
    localStorage.setItem("study_buddy_user_id", newId)
    return newId
  })

  // Topic-centric model - no sessions
  const { messages, isLoading, sendMessage, clearMessages } = useChat(userId)
  const [profile, setProfile] = useState<{
    knowledge_level: string
    all_topics: string[]
    strong_topics: string[]
    weak_topics: string[]
    known_concepts: string[]
    weak_areas: string[]
    mastery: number  // Overall mastery (0-1), calculated dynamically from assessed topics
  }>({
    knowledge_level: "Beginner",
    all_topics: [],
    strong_topics: [],
    weak_topics: [],
    known_concepts: [],
    weak_areas: [],
    mastery: 0,
  })

  const [topicsData, setTopicsData] = useState<{
    all_topics: TopicData[]
    weak_topics: TopicData[]
    strong_topics: TopicData[]
  }>({
    all_topics: [],
    weak_topics: [],
    strong_topics: []
  })

  const [assessmentState, setAssessmentState] = useState<{
    step: 'idle' | 'scope' | 'count' | 'active'
    type: 'MCQ' | 'QNA' | null
    selectedTopics: string[]
    questionCount: number | null
  }>({
    step: 'idle',
    type: null,
    selectedTopics: [],
    questionCount: null
  })

  const handleStartAssessment = (type: 'MCQ' | 'QNA') => {
    // Only allow topics that have been explained
    setAssessmentState({
      step: 'scope',
      type,
      selectedTopics: [],
      questionCount: null
    })
  }

  const handleToggleTopic = (topic: string) => {
    setAssessmentState(prev => ({
      ...prev,
      selectedTopics: prev.selectedTopics.includes(topic)
        ? prev.selectedTopics.filter(t => t !== topic)
        : [...prev.selectedTopics, topic]
    }))
  }

  const handleSetQuestionCount = (count: number) => {
    setAssessmentState(prev => ({
      ...prev,
      step: 'count',
      questionCount: count
    }))
  }

  const handleConfirmAssessment = async () => {
    setAssessmentState(prev => ({ ...prev, step: 'active' }))
  }

  const handleCancelAssessment = () => {
    setAssessmentState({
      step: 'idle',
      type: null,
      selectedTopics: [],
      questionCount: null
    })
  }

  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (lastMessage?.sender === 'ai' && lastMessage.metadata?.assessment_completed) {
      setAssessmentState({
        step: 'idle',
        type: null,
        selectedTopics: [],
        questionCount: null
      })
    }
  }, [messages])

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await chatApi.getProfile(userId)
        setProfile(data)
      } catch (err) {
        console.error("Failed to fetch profile", err)
      }
    }
    fetchProfile()
  }, [userId, messages.length])

  useEffect(() => {
    const fetchTopics = async () => {
      try {
        const data = await chatApi.getTopics(userId)
        setTopicsData(data)
      } catch (err) {
        console.error("Failed to fetch topics", err)
      }
    }
    fetchTopics()
  }, [userId, messages.length])

  const handleReset = async () => {
    if (confirm("Reset all learning progress? This cannot be undone.")) {
      await chatApi.resetMemory(userId)
      window.location.reload()
    }
  }

  const handleNewSession = async () => {
    // Only clear chat history - topics, mastery, and classifications are preserved
    await clearMessages()
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-primary/30">
        {/* Sidebar */}
        <aside className="w-[320px] h-full px-8 py-10 flex-shrink-0 z-20 border-r border-white/5 bg-black/20 backdrop-blur-3xl overflow-y-auto">
          <AIMemoryPanel
            level={profile.knowledge_level}
            concepts={profile.known_concepts}
            weakAreas={profile.weak_areas}
            allTopics={topicsData.all_topics}
            weakTopics={topicsData.weak_topics}
            strongTopics={topicsData.strong_topics}
            overallMastery={profile.mastery}
            onReset={handleReset}
            onNewSession={handleNewSession}
            assessmentState={assessmentState}
            onStartAssessment={handleStartAssessment}
            onToggleTopic={handleToggleTopic}
            onSetQuestionCount={handleSetQuestionCount}
            onConfirmAssessment={handleConfirmAssessment}
            onCancelAssessment={handleCancelAssessment}
          />
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col relative h-full">
          {assessmentState.step === 'active' && assessmentState.type === 'MCQ' ? (
            <MCQAssessment
              userId={userId}
              topics={assessmentState.selectedTopics}
              questionCount={assessmentState.questionCount || 10}
              onComplete={handleCancelAssessment}
              onCancel={handleCancelAssessment}
            />
          ) : assessmentState.step === 'active' && assessmentState.type === 'QNA' ? (
            <QnAAssessment
              userId={userId}
              topics={assessmentState.selectedTopics}
              questionCount={assessmentState.questionCount || 5}
              onComplete={handleCancelAssessment}
              onCancel={handleCancelAssessment}
            />
          ) : (
            <ChatWindow
              messages={messages}
              onSendMessage={sendMessage}
              isLoading={isLoading}
              profile={profile}
              disabled={false}
              onCancelAssessment={handleCancelAssessment}
              isAssessmentActive={assessmentState.step === 'active'}
            />
          )}
        </main>
      </div>
    </TooltipProvider>
  )
}

export default ChatPage
