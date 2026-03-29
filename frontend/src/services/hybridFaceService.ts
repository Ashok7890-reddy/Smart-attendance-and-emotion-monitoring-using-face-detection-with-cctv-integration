import { onnxFaceService } from './onnxFaceService'
import { faceApiService } from './faceApiService'

export class HybridFaceService {
  private preferONNX = true
  private onnxAvailable = false
  private performanceStats = {
    onnxSuccess: 0,
    onnxFallback: 0,
    faceApiUsage: 0,
    totalProcessingTime: 0
  }

  constructor() {
    this.initializeONNX()
  }

  private async initializeONNX() {
    try {
      await onnxFaceService.loadModels()
      this.onnxAvailable = true
      console.log('🎯 ONNX models loaded successfully - High accuracy mode enabled')
    } catch (error) {
      console.warn('⚠️ ONNX models failed to load, using face-api.js fallback')
      this.onnxAvailable = false
      this.preferONNX = false
    }
  }

  async detectAndRecognizeFaces(imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement) {
    const startTime = performance.now()
    
    // Try ONNX first if available and preferred
    if (this.preferONNX && this.onnxAvailable) {
      try {
        console.log('🚀 Using ONNX pipeline for high-accuracy detection...')
        const result = await onnxFaceService.processFaceRecognition(imageElement)
        
        if (result.faces.length > 0) {
          this.performanceStats.onnxSuccess++
          const totalTime = performance.now() - startTime
          this.performanceStats.totalProcessingTime += totalTime
          
          console.log(`✅ ONNX pipeline successful: ${result.faces.length} faces with high-quality embeddings`)
          return {
            faces: result.faces.map(face => ({
              detection: face.detection,
              descriptor: face.embedding, // 512D ArcFace embedding
              confidence: face.confidence,
              landmarks: face.landmarks,
              modelUsed: 'ONNX-ArcFace',
              embeddingDimension: 512
            })),
            processingTime: totalTime,
            modelUsed: 'ONNX (YuNet + ArcFace)',
            accuracy: 'High'
          }
        } else {
          console.log('🔄 ONNX detected no faces, trying face-api.js...')
          this.performanceStats.onnxFallback++
        }
      } catch (error) {
        console.error('❌ ONNX pipeline failed:', error)
        console.log('🔄 Falling back to face-api.js...')
        this.performanceStats.onnxFallback++
      }
    }

    // Fallback to face-api.js
    try {
      console.log('🔄 Using face-api.js pipeline...')
      const detections = await faceApiService.detectMultipleFaces(imageElement)
      
      this.performanceStats.faceApiUsage++
      const totalTime = performance.now() - startTime
      this.performanceStats.totalProcessingTime += totalTime

      const faces = detections.map(detection => ({
        detection: {
          x: detection.detection.box.x,
          y: detection.detection.box.y,
          width: detection.detection.box.width,
          height: detection.detection.box.height,
          confidence: detection.detection.score
        },
        descriptor: detection.descriptor, // 128D face-api.js embedding
        confidence: detection.detection.score,
        landmarks: detection.landmarks,
        modelUsed: 'face-api.js',
        embeddingDimension: 128
      }))

      console.log(`✅ face-api.js pipeline: ${faces.length} faces detected`)
      return {
        faces: faces,
        processingTime: totalTime,
        modelUsed: 'face-api.js (TinyFaceDetector + FaceNet)',
        accuracy: 'Standard'
      }
    } catch (error) {
      console.error('❌ Both ONNX and face-api.js failed:', error)
      return {
        faces: [],
        processingTime: performance.now() - startTime,
        modelUsed: 'None',
        error: error.message
      }
    }
  }

  async detectSingleFace(imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement) {
    const result = await this.detectAndRecognizeFaces(imageElement)
    
    if (result.faces.length > 0) {
      // Return the face with highest confidence
      const bestFace = result.faces.reduce((best, current) => 
        current.confidence > best.confidence ? current : best
      )
      
      return {
        ...bestFace,
        processingTime: result.processingTime,
        modelUsed: result.modelUsed
      }
    }
    
    return null
  }

  // Intelligent face comparison that handles both ONNX and face-api.js embeddings
  compareFaces(descriptor1: Float32Array, descriptor2: Float32Array, model1?: string, model2?: string): number {
    // Check if both are ONNX embeddings (512D)
    if (descriptor1.length === 512 && descriptor2.length === 512) {
      return onnxFaceService.compareFaceEmbeddings(descriptor1, descriptor2)
    }
    
    // Check if both are face-api.js embeddings (128D)
    if (descriptor1.length === 128 && descriptor2.length === 128) {
      return faceApiService.compareFaces(descriptor1, descriptor2)
    }
    
    // Mixed embeddings - cannot compare directly
    console.warn('⚠️ Cannot compare embeddings of different dimensions:', descriptor1.length, 'vs', descriptor2.length)
    console.warn('Models:', model1, 'vs', model2)
    return 0
  }

  // Enhanced image preprocessing for optimal results
  async createOptimizedImageElement(base64Data: string): Promise<HTMLImageElement> {
    if (this.onnxAvailable && this.preferONNX) {
      return onnxFaceService.createOptimizedImageElement(base64Data)
    } else {
      return faceApiService.createImageElement(base64Data)
    }
  }

  // Performance and accuracy monitoring
  getPerformanceStats() {
    const total = this.performanceStats.onnxSuccess + this.performanceStats.onnxFallback + this.performanceStats.faceApiUsage
    
    if (total === 0) return null
    
    const onnxStats = onnxFaceService.getPerformanceStats()
    const faceApiStats = faceApiService.getPerformanceStats()
    
    return {
      totalProcessed: total,
      onnxSuccessRate: (this.performanceStats.onnxSuccess / total) * 100,
      onnxFallbackRate: (this.performanceStats.onnxFallback / total) * 100,
      faceApiUsageRate: (this.performanceStats.faceApiUsage / total) * 100,
      averageProcessingTime: this.performanceStats.totalProcessingTime / total,
      onnxAvailable: this.onnxAvailable,
      preferredModel: this.preferONNX ? 'ONNX' : 'face-api.js',
      onnxStats: onnxStats,
      faceApiStats: faceApiStats,
      accuracy: this.onnxAvailable ? 'High (ONNX + ArcFace)' : 'Standard (face-api.js)'
    }
  }

  // Model preference management
  setPreferONNX(prefer: boolean) {
    this.preferONNX = prefer && this.onnxAvailable
    console.log(`🔧 Model preference set to: ${this.preferONNX ? 'ONNX (High Accuracy)' : 'face-api.js (Standard)'}`)
  }

  isONNXAvailable(): boolean {
    return this.onnxAvailable
  }

  // Batch processing for multiple images
  async processBatch(images: (HTMLImageElement | HTMLVideoElement | HTMLCanvasElement)[], maxConcurrent = 3) {
    const results = []
    
    // Process in batches to avoid overwhelming the system
    for (let i = 0; i < images.length; i += maxConcurrent) {
      const batch = images.slice(i, i + maxConcurrent)
      const batchPromises = batch.map(img => this.detectAndRecognizeFaces(img))
      const batchResults = await Promise.all(batchPromises)
      results.push(...batchResults)
    }
    
    return results
  }

  // Quality assessment for embeddings
  assessEmbeddingQuality(descriptor: Float32Array, modelUsed: string): { quality: string; score: number; recommendations: string[] } {
    const recommendations = []
    let quality = 'Good'
    let score = 0.8
    
    if (modelUsed.includes('ONNX')) {
      // ArcFace embeddings (512D)
      const norm = Math.sqrt(descriptor.reduce((sum, val) => sum + val * val, 0))
      
      if (norm > 0.95 && norm < 1.05) {
        quality = 'Excellent'
        score = 0.95
      } else if (norm > 0.9 && norm < 1.1) {
        quality = 'Good'
        score = 0.85
      } else {
        quality = 'Fair'
        score = 0.7
        recommendations.push('Consider better lighting or image quality')
      }
      
      // Check for embedding diversity
      const variance = descriptor.reduce((sum, val) => sum + val * val, 0) / descriptor.length
      if (variance < 0.01) {
        recommendations.push('Low embedding variance - may indicate poor face quality')
      }
    } else {
      // face-api.js embeddings (128D)
      const sum = descriptor.reduce((sum, val) => sum + Math.abs(val), 0)
      
      if (sum > 10) {
        quality = 'Good'
        score = 0.8
      } else if (sum > 5) {
        quality = 'Fair'
        score = 0.6
      } else {
        quality = 'Poor'
        score = 0.4
        recommendations.push('Very low quality embedding - retake photo')
      }
    }
    
    return { quality, score, recommendations }
  }
}

export const hybridFaceService = new HybridFaceService()