import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, XCircle, ArrowRight, Loader2, Award, FileText, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Textarea } from "@/components/ui/textarea"
import { chatApi } from "@/services/api"

interface QnAAssessmentProps {
  userId: string
  topics: string[]
  questionCount: number
  onComplete: () => void
  onCancel: () => void
}

interface Question {
  question: string
  length: string
}

interface AssessmentResult {
  concept_score: number
  completeness_score: number
  clarity_score: number
  total_marks: number
  result: string  // "correct" | "incorrect"
  feedback: string
  rubric_evaluation: string
  correct_explanation: string
  mastery_score?: number
  status?: string
  classification?: string  // "weak" | "strong" | "unassessed"
  questions_attempted?: number
  correct_answers?: number
  is_valid_answer?: boolean
  explanation_provided?: boolean
  evaluation_error?: boolean
}

const QnAAssessment: React.FC<QnAAssessmentProps> = ({
  userId,
  topics,
  questionCount,
  onComplete,
  onCancel
}) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [userAnswer, setUserAnswer] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [evaluation, setEvaluation] = useState<AssessmentResult | null>(null)
  const [totalScore, setTotalScore] = useState(0)
  const [isFinished, setIsFinished] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [canGoNext, setCanGoNext] = useState(false)
  const [explanationShown, setExplanationShown] = useState(false)  // MANDATORY: Track explanation display
  const [validationError, setValidationError] = useState<string | null>(null)  // Input validation error

  // MANDATORY: Input validation helper
  const isGibberishAnswer = (answer: string): boolean => {
    if (!answer || !answer.trim()) return true
    const cleaned = answer.trim()
    if (cleaned.length < 3) return true
    
    // Check if mostly non-alphabetic
    const alphaChars = (cleaned.match(/[a-zA-Z]/g) || []).length
    if (cleaned.length > 0 && alphaChars / cleaned.length < 0.5) return true
    
    // Check for keyboard mashing patterns
    const gibberishPatterns = [
      /^[asdfghjklqwertyuiopzxcvbnm]{3,}$/i,
      /^[a-z]{1,3}(\s+[a-z]{1,3}){0,5}$/i,
      /^[^a-zA-Z]*$/,
      /^(.{1,2})\1{2,}$/
    ]
    const lower = cleaned.toLowerCase()
    for (const pattern of gibberishPatterns) {
      if (pattern.test(lower)) return true
    }
    
    // Check for meaningful words
    const words = cleaned.match(/[a-zA-Z]{3,}/g)
    if (!words || words.length === 0) return true
    
    // Check for common gibberish
    const gibberishWords = ['asdf', 'qwerty', 'zxcv', 'aaa', 'bbb', 'xxx', 'yyy', 'zzz']
    if (words.every(w => gibberishWords.includes(w.toLowerCase()))) return true
    
    return false
  }

  const loadNextQuestion = async () => {
    setIsLoading(true)
    setError(null)
    setValidationError(null)
    setUserAnswer("")
    setEvaluation(null)
    setCanGoNext(false)
    setExplanationShown(false)  // Reset explanation flag for new question

    try {
      const topic = topics[currentQuestionIndex % topics.length]
      const data = await chatApi.generateQnA(userId, topic)
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
    if (!currentQuestion) return
    
    // MANDATORY: Validate input - empty, random characters, or meaningless = INVALID
    setValidationError(null)
    
    if (!userAnswer || userAnswer.trim().length < 3) {
      setValidationError("Please provide a meaningful answer. Empty or very short answers are marked as INCORRECT.")
      return
    }
    
    if (isGibberishAnswer(userAnswer)) {
      setValidationError("Your answer appears to be random characters or gibberish. Please provide a meaningful response that addresses the question.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    const topic = topics[currentQuestionIndex % topics.length]
    
    try {
      const result = await chatApi.submitQnA(userId, topic, userAnswer)
      
      // MANDATORY: Check for evaluation errors
      if (result.evaluation_error) {
        setError("Assessment evaluation failed. Please retry.")
        setIsSubmitting(false)
        return
      }
      
      setEvaluation(result)
      setTotalScore(prev => prev + result.total_marks)
      
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
    const maxPossibleMarks = questionCount * 10
    const percentage = Math.round((totalScore / maxPossibleMarks) * 100)
    
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
          <p className="text-muted-foreground">You've completed the Q&A assessment on {topics.join(", ")}</p>
        </div>

        <div className="grid grid-cols-2 gap-4 w-full">
          <Card className="p-4 bg-white/5 border-white/10">
            <p className="text-2xl font-bold text-white">{totalScore} / {maxPossibleMarks}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Total Marks</p>
          </Card>
          <Card className="p-4 bg-white/5 border-white/10">
            <p className="text-2xl font-bold text-white">{percentage}%</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Overall Performance</p>
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
          <h3 className="text-sm font-bold uppercase tracking-widest text-primary">Q&A Assessment</h3>
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
        <div className="flex-1 flex flex-col space-y-6 overflow-y-auto pr-2 scrollbar-hide">
          {/* Question */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-2">
              <div className="px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-[9px] font-bold text-primary uppercase">
                {currentQuestion?.length} Answer
              </div>
            </div>
            <h2 className="text-xl font-medium text-white/90 leading-relaxed">
              {currentQuestion?.question}
            </h2>
          </motion.div>

          {/* Answer Area */}
          <div className="space-y-2">
            <div className="flex justify-between items-end">
               <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/50">Your Answer</label>
               <span className={`text-[10px] font-mono ${userAnswer.length >= 50 ? 'text-emerald-500' : userAnswer.length >= 10 ? 'text-amber-500' : 'text-muted-foreground'}`}>
                 {userAnswer.length} chars {userAnswer.length < 10 && "(min 10)"}
               </span>
            </div>
            {/* MANDATORY: Show validation error */}
            {validationError && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs">
                {validationError}
              </div>
            )}
            <Textarea
              placeholder="Type your answer here... (at least 50 characters recommended for full marks)"
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              disabled={!!evaluation || isSubmitting}
              className="min-h-[200px] bg-white/5 border-white/10 focus:border-primary/50 text-white resize-none rounded-xl p-4"
            />
          </div>

          {/* Feedback Section */}
          <AnimatePresence>
            {evaluation && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Rubric Scores */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
                    <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-wider">Correctness</p>
                    <p className="text-lg font-bold text-white">{evaluation.concept_score}/5</p>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
                    <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-wider">Completeness</p>
                    <p className="text-lg font-bold text-white">{evaluation.completeness_score}/3</p>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
                    <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-wider">Clarity</p>
                    <p className="text-lg font-bold text-white">{evaluation.clarity_score}/2</p>
                  </div>
                </div>

                <div className={`p-5 rounded-2xl border ${evaluation.total_marks >= 7 ? "bg-emerald-500/10 border-emerald-500/20" : evaluation.total_marks >= 4 ? "bg-amber-500/10 border-amber-500/20" : "bg-destructive/10 border-destructive/20"}`}>
                  <div className="flex items-start gap-3">
                    {evaluation.total_marks >= 7 ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5" />
                    ) : evaluation.total_marks >= 4 ? (
                        <Info className="w-5 h-5 text-amber-500 mt-0.5" />
                    ) : (
                      <XCircle className="w-5 h-5 text-destructive mt-0.5" />
                    )}
                    <div className="space-y-3 flex-1">
                      <div className="flex items-center justify-between">
                        <p className={`text-sm font-bold ${evaluation.total_marks >= 7 ? "text-emerald-500" : evaluation.total_marks >= 4 ? "text-amber-500" : "text-destructive"}`}>
                          {evaluation.total_marks >= 7 ? "Excellent Work!" : evaluation.total_marks >= 4 ? "Good Start" : "Needs Review"}
                        </p>
                        {/* MANDATORY: Show classification and status */}
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
                      
                      {/* MANDATORY: Result indicator */}
                      <div className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase w-fit ${
                        evaluation.result === "correct" 
                          ? "bg-emerald-500/20 text-emerald-500"
                          : "bg-destructive/20 text-destructive"
                      }`}>
                        {evaluation.result === "correct" ? "✓ Correct (Counts for Mastery)" : "✗ Incorrect"}
                      </div>
                      
                      <div className="space-y-2">
                        <p className="text-xs text-white/90 font-medium">Feedback:</p>
                        <p className="text-xs text-white/70 leading-relaxed italic">
                          "{evaluation.feedback}"
                        </p>
                      </div>

                      <div className="space-y-2">
                        <p className="text-xs text-white/90 font-medium flex items-center gap-1.5">
                            <FileText className="w-3 h-3 text-primary" />
                            Rubric Breakdown:
                        </p>
                        <p className="text-xs text-white/70 leading-relaxed">
                          {evaluation.rubric_evaluation}
                        </p>
                      </div>

                      <div className="space-y-2 pt-1">
                        <p className="text-xs text-white/90 font-medium">Model Answer:</p>
                        <div className="p-3 rounded-lg bg-black/40 border border-white/5 text-xs text-white/70 leading-relaxed">
                          {evaluation.correct_explanation}
                        </div>
                      </div>

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
                      {/* MANDATORY: Show questions attempted / correct */}
                      {evaluation.questions_attempted !== undefined && (
                        <p className="text-[10px] text-muted-foreground">
                          {evaluation.correct_answers} / {evaluation.questions_attempted} correct on this topic
                        </p>
                      )}
                    </div>
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
            disabled={userAnswer.length < 10 || isSubmitting}
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

export default QnAAssessment
