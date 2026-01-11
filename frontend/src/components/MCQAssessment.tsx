import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, XCircle, ArrowRight, Loader2, Award } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { chatApi } from "@/services/api"

interface MCQAssessmentProps {
  userId: string
  topics: string[]
  questionCount: number
  onComplete: () => void
  onCancel: () => void
}

interface Question {
  question: string
  options: Record<string, string>
  correct_answer?: string
  explanation?: string
}

interface AssessmentResult {
  is_correct: boolean
  feedback: string
  correct_explanation: string
  mastery_score?: number
  status?: string
  classification?: string  // "weak" | "strong" | "unassessed"
  questions_attempted?: number
  correct_answers?: number
  explanation_provided?: boolean
  evaluation_error?: boolean
}

const MCQAssessment: React.FC<MCQAssessmentProps> = ({
  userId,
  topics,
  questionCount,
  onComplete,
  onCancel
}) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [evaluation, setEvaluation] = useState<AssessmentResult | null>(null)
  const [correctAnswers, setCorrectAnswers] = useState(0)
  const [isFinished, setIsFinished] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [canGoNext, setCanGoNext] = useState(false)
  const [explanationShown, setExplanationShown] = useState(false)  // MANDATORY: Track explanation display

  const loadNextQuestion = async () => {
    setIsLoading(true)
    setError(null)
    setSelectedOption(null)
    setEvaluation(null)
    setCanGoNext(false)
    setExplanationShown(false)  // Reset explanation flag for new question

    try {
      // Pick a topic randomly or sequentially
      const topic = topics[currentQuestionIndex % topics.length]
      const data = await chatApi.generateMCQ(userId, topic)
      
      setCurrentQuestion(data)
    } catch (err) {
      setError("Failed to load question. Please try again.")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadNextQuestion()
  }, [])

  const handleSubmit = async () => {
    // MANDATORY: User must select exactly ONE option
    if (!selectedOption || !currentQuestion) {
      setError("Please select an option before submitting.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    const topic = topics[currentQuestionIndex % topics.length]
    
    try {
      const result = await chatApi.submitMCQ(userId, topic, selectedOption)
      
      // MANDATORY: Check for evaluation errors
      if (result.evaluation_error) {
        setError("Assessment evaluation failed. Please retry.")
        setIsSubmitting(false)
        return
      }
      
      setEvaluation(result)
      
      // MANDATORY: Update correct answers count
      if (result.is_correct) {
        setCorrectAnswers(prev => prev + 1)
      }
      
      // MANDATORY: Verify explanation was provided
      if (!result.feedback && !result.correct_explanation) {
        setError("Assessment evaluation failed. No explanation provided. Please retry.")
        setIsSubmitting(false)
        return
      }
      
      // MANDATORY: Mark explanation as shown
      setExplanationShown(true)
      
      // MANDATORY: Wait for user to read explanation before allowing next question
      // 2-second minimum delay ensures explanation is displayed
      setTimeout(() => {
        setCanGoNext(true)
      }, 2000)
    } catch (err) {
      console.error(err)
      // FAILURE RULE: Show error, do not allow silent behavior
      setError("Assessment evaluation failed. Please retry.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleNext = () => {
    // MANDATORY: Cannot proceed without explanation being shown
    if (!explanationShown) {
      setError("Please review the explanation before proceeding.")
      return
    }
    
    if (currentQuestionIndex + 1 < questionCount) {
      setCurrentQuestionIndex(prev => prev + 1)
      loadNextQuestion()
    } else {
      setIsFinished(true)
    }
  }

  if (isFinished) {
    const percentage = Math.round((correctAnswers / questionCount) * 100)
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center space-y-8 max-w-2xl mx-auto">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="p-6 rounded-full bg-primary/20 border-4 border-primary/30"
        >
          <Award className="w-20 h-20 text-primary" />
        </motion.div>
        
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-white">Assessment Complete!</h2>
          <p className="text-muted-foreground">You've completed the assessment on {topics.join(", ")}</p>
        </div>

        <div className="grid grid-cols-2 gap-4 w-full">
          <Card className="p-4 bg-white/5 border-white/10">
            <p className="text-2xl font-bold text-white">{correctAnswers} / {questionCount}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Correct Answers</p>
          </Card>
          <Card className="p-4 bg-white/5 border-white/10">
            <p className="text-2xl font-bold text-white">{percentage}%</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Score</p>
          </Card>
        </div>

        <div className="flex flex-col gap-3 w-full">
          <Button onClick={onComplete} className="w-full h-12 text-lg font-semibold">
            Return to Learning
          </Button>
          <Button variant="ghost" onClick={onCancel} className="text-muted-foreground hover:text-white">
            Close
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h3 className="text-sm font-bold uppercase tracking-widest text-primary">MCQ Assessment</h3>
          <p className="text-[10px] text-muted-foreground">Question {currentQuestionIndex + 1} of {questionCount}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={onCancel} className="text-muted-foreground hover:text-destructive">
          <XCircle className="w-4 h-4 mr-2" />
          Quit
        </Button>
      </div>

      <Progress value={((currentQuestionIndex) / questionCount) * 100} className="h-1 bg-white/5" />

      {isLoading ? (
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground animate-pulse">Generating your next challenge...</p>
        </div>
      ) : error ? (
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <p className="text-destructive text-sm">{error}</p>
          <Button onClick={loadNextQuestion}>Retry</Button>
        </div>
      ) : (
        <div className="flex-1 flex flex-col space-y-8 overflow-y-auto pr-2 scrollbar-hide">
          {/* Question */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-4"
          >
            <h2 className="text-xl font-medium text-white/90 leading-relaxed">
              {currentQuestion?.question}
            </h2>
          </motion.div>

          {/* Options */}
          <div className="grid grid-cols-1 gap-3">
            {currentQuestion && Object.entries(currentQuestion.options).map(([key, value]) => {
              const isSelected = selectedOption === key
              // Track evaluation state for styling - using underscore prefix to indicate intentionally unused
              const _isCorrect = evaluation?.is_correct && isSelected
              const _isWrong = evaluation && !evaluation.is_correct && isSelected
              void _isCorrect; void _isWrong; // suppress lint warnings
              
              // More robust check: backend should ideally return which key was correct in evaluation
              // For now we'll rely on the evaluation feedback or just highlight the selected one if we don't have the correct key.
              
              return (
                <button
                  key={key}
                  disabled={!!evaluation || isSubmitting}
                  onClick={() => setSelectedOption(key)}
                  className={`
                    flex items-center gap-4 p-4 rounded-xl border transition-all text-left group
                    ${isSelected 
                      ? "bg-primary/20 border-primary/50 text-white" 
                      : "bg-white/5 border-white/5 text-white/70 hover:bg-white/10 hover:border-white/20"}
                    ${evaluation && isSelected ? (evaluation.is_correct ? "bg-emerald-500/20 border-emerald-500/50" : "bg-destructive/20 border-destructive/50") : ""}
                  `}
                >
                  <div className={`
                    w-8 h-8 flex items-center justify-center rounded-lg border text-sm font-bold
                    ${isSelected ? "bg-primary text-white border-primary" : "bg-black/40 border-white/10 text-white/40"}
                    ${evaluation && isSelected ? (evaluation.is_correct ? "bg-emerald-500 border-emerald-500" : "bg-destructive border-destructive") : ""}
                  `}>
                    {key}
                  </div>
                  <span className="flex-1 text-sm">{value}</span>
                  {evaluation && isSelected && (
                    evaluation.is_correct ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-destructive" />
                  )}
                </button>
              )
            })}
          </div>

          {/* Feedback Section */}
          <AnimatePresence>
            {evaluation && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-5 rounded-2xl border ${evaluation.is_correct ? "bg-emerald-500/10 border-emerald-500/20" : "bg-destructive/10 border-destructive/20"}`}
              >
                <div className="flex items-start gap-3">
                  {evaluation.is_correct ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5" />
                  ) : (
                    <XCircle className="w-5 h-5 text-destructive mt-0.5" />
                  )}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className={`text-sm font-bold ${evaluation.is_correct ? "text-emerald-500" : "text-destructive"}`}>
                        {evaluation.is_correct ? "Excellent!" : "Not quite right"}
                      </p>
                      {/* MANDATORY: Show classification status */}
                      <div className="flex items-center gap-2">
                        {evaluation.classification && (
                          <div className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${
                            evaluation.classification === "strong" 
                              ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-500"
                              : evaluation.classification === "weak"
                              ? "bg-destructive/10 border border-destructive/20 text-destructive"
                              : "bg-primary/10 border border-primary/20 text-primary"
                          }`}>
                            {evaluation.classification}
                          </div>
                        )}
                        {evaluation.status && (
                          <div className="px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-[9px] font-bold text-primary uppercase">
                            {evaluation.status}
                          </div>
                        )}
                      </div>
                    </div>
                    {/* MANDATORY: Display feedback explanation */}
                    <p className="text-xs text-white/80 leading-relaxed">
                      {evaluation.feedback}
                    </p>
                    {/* MANDATORY: Display correct explanation */}
                    <p className="text-xs text-white/80 leading-relaxed">
                      {evaluation.correct_explanation}
                    </p>
                    {/* MANDATORY: Show mastery progress */}
                    {evaluation.mastery_score !== undefined && (
                      <div className="pt-2 flex items-center gap-2">
                        <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                          <div 
                            className={`h-full transition-all duration-1000 ${
                              evaluation.mastery_score >= 0.40 ? "bg-emerald-500" : "bg-destructive"
                            }`}
                            style={{ width: `${evaluation.mastery_score * 100}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {Math.round(evaluation.mastery_score * 100)}% Mastery
                        </span>
                      </div>
                    )}
                    {/* Show questions attempted / correct */}
                    {evaluation.questions_attempted !== undefined && (
                      <p className="text-[10px] text-muted-foreground">
                        {evaluation.correct_answers} / {evaluation.questions_attempted} correct on this topic
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Footer Actions */}
      <div className="pt-4 border-t border-white/5 flex flex-col gap-2">
        {/* MANDATORY: Show error if evaluation failed */}
        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs text-center">
            {error}
          </div>
        )}
        
        {!evaluation ? (
          <Button
            onClick={handleSubmit}
            disabled={!selectedOption || isSubmitting}
            className="w-full h-12 rounded-xl bg-primary hover:bg-primary/90 text-white font-bold"
          >
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Submit Answer"}
          </Button>
        ) : (
          <Button
            onClick={handleNext}
            disabled={!canGoNext || !explanationShown}
            className="w-full h-12 rounded-xl bg-white text-black hover:bg-white/90 font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {currentQuestionIndex + 1 === questionCount ? "View Results" : (
              canGoNext && explanationShown ? "Next Question" : `Reviewing explanation...`
            )}
            <ArrowRight className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

export default MCQAssessment
