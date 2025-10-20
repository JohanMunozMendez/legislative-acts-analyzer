"use client"

import type React from "react"

import { useState } from "react"
import { Upload, FileText, Download, Trash2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Analysis {
  id: string
  filename: string
  date: string
  content: string
  originalText: string
}

export default function LegislativeActsAnalyzer() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadedFile(file)
  }

  const handleAnalyze = async () => {
    if (!uploadedFile) return

    setIsAnalyzing(true)

    try {
      // Read the full file content
      const fileContent = await uploadedFile.text()

      // TODO: Replace with your actual FastAPI endpoint
      // const formData = new FormData()
      // formData.append('file', uploadedFile)
      // const response = await fetch('YOUR_FASTAPI_ENDPOINT', {
      //   method: 'POST',
      //   body: formData,
      // })
      // const result = await response.json()

      // Simulated analysis result (replace with actual API call)
      const mockAnalysis = `Analysis of ${uploadedFile.name}:\n\nThis legislative act contains ${fileContent.split(" ").length} words and ${fileContent.split("\n").length} lines.\n\nKey sections identified:\n- Preamble\n- Main provisions\n- Enforcement clauses\n\nSummary: This document outlines legislative provisions...`

      const newAnalysis: Analysis = {
        id: Date.now().toString(),
        filename: uploadedFile.name,
        date: new Date().toLocaleString(),
        content: mockAnalysis,
        originalText: fileContent,
      }

      setAnalyses([newAnalysis, ...analyses])
      setSelectedAnalysis(newAnalysis)
    } catch (error) {
      console.error("Analysis failed:", error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleRemove = () => {
    setUploadedFile(null)
  }

  const handleExportPDF = () => {
    if (!selectedAnalysis) return
    // Simple PDF export simulation - in production, use a library like jsPDF
    alert("PDF export functionality - integrate with jsPDF or similar library")
  }

  const handleExportTXT = () => {
    if (!selectedAnalysis) return
    const blob = new Blob([selectedAnalysis.content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${selectedAnalysis.filename}_analysis.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Legislative Acts Analyzer</h1>
          <p className="text-slate-600">Upload and analyze legislative documents with AI-powered insights</p>
        </header>

        {/* Main Content - Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
          {/* Left Column - Upload Section (3 columns) */}
          <Card className="lg:col-span-3 p-6 bg-white shadow-lg">
            <h2 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Upload Document
            </h2>

            {/* Upload Area */}
            {!uploadedFile ? (
              <label className="flex flex-col items-center justify-center w-full min-h-64 border-2 border-dashed border-slate-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-slate-50 transition-colors">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <FileText className="w-12 h-12 text-slate-400 mb-3" />
                  <p className="mb-2 text-sm text-slate-600">
                    <span className="font-semibold">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-slate-500">TXT, PDF, DOC files supported</p>
                </div>
                <input type="file" className="hidden" accept=".txt,.pdf,.doc,.docx" onChange={handleFileUpload} />
              </label>
            ) : (
              <div className="space-y-4">
                {/* File Info */}
                <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <FileText className="w-8 h-8 text-blue-600" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 truncate">{uploadedFile.name}</p>
                    <p className="text-sm text-slate-600">{(uploadedFile.size / 1024).toFixed(2)} KB</p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <Button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing}
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      "Analyze"
                    )}
                  </Button>
                  <Button
                    onClick={handleRemove}
                    variant="outline"
                    className="flex-1 border-red-300 text-red-600 hover:bg-red-50 bg-transparent"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Remove
                  </Button>
                </div>
              </div>
            )}
          </Card>

          <Card className="lg:col-span-9 p-6 bg-white shadow-lg">
            {selectedAnalysis ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    {selectedAnalysis.filename}
                  </h2>
                  <div className="flex gap-2">
                    <Button
                      onClick={handleExportPDF}
                      variant="outline"
                      size="sm"
                      className="border-slate-300 bg-transparent"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      PDF
                    </Button>
                    <Button
                      onClick={handleExportTXT}
                      variant="outline"
                      size="sm"
                      className="border-slate-300 bg-transparent"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      TXT
                    </Button>
                  </div>
                </div>

                <ScrollArea className="h-[500px] w-full rounded-md border border-slate-200 bg-slate-50 p-6">
                  <div className="prose prose-slate max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-slate-700 leading-relaxed">
                      {selectedAnalysis.content}
                    </pre>
                  </div>
                </ScrollArea>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full min-h-[500px] text-center">
                <FileText className="w-16 h-16 text-slate-300 mb-3" />
                <p className="text-slate-500">No analysis selected</p>
                <p className="text-sm text-slate-400 mt-1">Upload and analyze a document to view results here</p>
              </div>
            )}
          </Card>
        </div>

        <Card className="p-6 bg-white shadow-lg">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Analysis History</h2>

          <ScrollArea className="h-[300px]">
            {analyses.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <FileText className="w-16 h-16 text-slate-300 mb-3" />
                <p className="text-slate-500">No analyses yet</p>
                <p className="text-sm text-slate-400 mt-1">Upload and analyze a document to get started</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {analyses.map((analysis) => (
                  <button
                    key={analysis.id}
                    onClick={() => setSelectedAnalysis(analysis)}
                    className={`text-left p-4 rounded-lg border transition-all ${
                      selectedAnalysis?.id === analysis.id
                        ? "bg-blue-50 border-blue-300 shadow-sm"
                        : "bg-slate-50 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 truncate">{analysis.filename}</p>
                        <p className="text-xs text-slate-500 mt-1">{analysis.date}</p>
                      </div>
                      <FileText className="w-5 h-5 text-slate-400 flex-shrink-0" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}
