import * as faceapi from 'face-api.js';

export class FaceApiService {
  private modelsLoaded = false;
  private loadingPromise: Promise<void> | null = null;
  private performanceStats = {
    detectionTimes: [] as number[],
    recognitionTimes: [] as number[],
    modelUsage: { tiny: 0, ssd: 0 }
  };

  async loadModels() {
    // If already loaded, return immediately
    if (this.modelsLoaded) {
      return;
    }

    // If currently loading, wait for that to finish
    if (this.loadingPromise) {
      return this.loadingPromise;
    }

    // Start loading
    this.loadingPromise = this._loadModels();
    await this.loadingPromise;
    this.loadingPromise = null;
  }

  private async _loadModels() {
    try {
      const MODEL_URL = '/models';
      
      console.log('🚀 Loading EFFICIENT face-api.js models from:', MODEL_URL);
      console.log('Current URL:', window.location.href);
      
      // Load TinyFaceDetector (faster and more efficient than SSD MobileNet)
      console.log('Loading TinyFaceDetector (Efficient)...');
      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
      console.log('✅ TinyFaceDetector loaded (Fast & Accurate)');
      
      // Also load SSD MobileNet as fallback
      console.log('Loading SSD MobileNet v1 (Fallback)...');
      await faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL);
      console.log('✅ SSD MobileNet v1 loaded');
      
      console.log('Loading Face Landmark 68 (High Precision)...');
      await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
      console.log('✅ Face Landmark 68 loaded');
      
      console.log('Loading Face Recognition Net (FaceNet)...');
      await faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
      console.log('✅ Face Recognition loaded');
      
      console.log('Loading Face Expression Net...');
      await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);
      console.log('✅ Face Expression loaded - Emotion detection ready!');
      
      this.modelsLoaded = true;
      console.log('🎯 All EFFICIENT face-api.js models loaded successfully!');
      console.log('📊 Using TinyFaceDetector for optimal speed and accuracy');
    } catch (error) {
      console.error('❌ Error loading face-api models:', error);
      console.error('Error details:', error);
      throw new Error(`Failed to load face recognition models: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async detectFace(imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement) {
    await this.loadModels();
    const startTime = performance.now();

    try {
      let detection = null;
      let modelUsed = '';

      // Try TinyFaceDetector first (faster and more efficient)
      const tinyStartTime = performance.now();
      detection = await faceapi
        .detectSingleFace(imageElement, new faceapi.TinyFaceDetectorOptions({ 
          inputSize: 416,      // Optimal size for speed/accuracy balance
          scoreThreshold: 0.5  // Good balance for detection
        }))
        .withFaceLandmarks()
        .withFaceDescriptor()
        .withFaceExpressions();

      if (detection) {
        modelUsed = 'TinyFaceDetector';
        this.performanceStats.modelUsage.tiny++;
        const tinyTime = performance.now() - tinyStartTime;
        console.log(`⚡ TinyFaceDetector: ${tinyTime.toFixed(1)}ms`);
      } else {
        // Fallback to SSD MobileNet
        console.log('🔄 TinyFaceDetector failed, trying SSD MobileNet...');
        const ssdStartTime = performance.now();
        detection = await faceapi
          .detectSingleFace(imageElement, new faceapi.SsdMobilenetv1Options({ 
            minConfidence: 0.6  // Lower confidence for fallback
          }))
          .withFaceLandmarks()
          .withFaceDescriptor()
          .withFaceExpressions();
        
        if (detection) {
          modelUsed = 'SSD MobileNet';
          this.performanceStats.modelUsage.ssd++;
          const ssdTime = performance.now() - ssdStartTime;
          console.log(`🐌 SSD MobileNet: ${ssdTime.toFixed(1)}ms`);
        }
      }

      const totalTime = performance.now() - startTime;
      this.performanceStats.detectionTimes.push(totalTime);

      if (detection) {
        console.log(`✅ Face detected using ${modelUsed} in ${totalTime.toFixed(1)}ms`);
        console.log('Face detection confidence:', detection.detection.score.toFixed(3));
        console.log('Face box:', detection.detection.box);
        console.log('Descriptor length:', detection.descriptor.length);
        
        // Validate descriptor quality
        const descriptorSum = detection.descriptor.reduce((sum, val) => sum + Math.abs(val), 0);
        console.log('Descriptor quality (sum of absolute values):', descriptorSum.toFixed(3));
        
        if (descriptorSum < 0.1) {
          console.warn('⚠️ Low quality face descriptor detected');
        } else {
          console.log('🎯 High quality face descriptor generated');
        }

        // Log performance stats periodically
        if (this.performanceStats.detectionTimes.length % 10 === 0) {
          this.logPerformanceStats();
        }
      }

      return detection;
    } catch (error) {
      console.error('Error detecting face:', error);
      return null;
    }
  }

  async detectMultipleFaces(imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement) {
    await this.loadModels();
    const startTime = performance.now();

    try {
      let detections: any[] = [];
      let modelUsed = '';

      // Try TinyFaceDetector first (faster for multiple faces)
      const tinyStartTime = performance.now();
      detections = await faceapi
        .detectAllFaces(imageElement, new faceapi.TinyFaceDetectorOptions({ 
          inputSize: 416,      // Optimal for multiple face detection
          scoreThreshold: 0.5  // Good balance for classroom scenarios
        }))
        .withFaceLandmarks()
        .withFaceDescriptors()
        .withFaceExpressions();

      const tinyTime = performance.now() - tinyStartTime;
      console.log(`⚡ TinyFaceDetector (Multiple): ${tinyTime.toFixed(1)}ms → ${detections.length} faces`);

      // If TinyFaceDetector finds few faces, try SSD MobileNet as well
      if (detections.length < 2) {
        console.log('🔄 TinyFaceDetector found few faces, trying SSD MobileNet...');
        const ssdStartTime = performance.now();
        const ssdDetections = await faceapi
          .detectAllFaces(imageElement, new faceapi.SsdMobilenetv1Options({ 
            minConfidence: 0.6
          }))
          .withFaceLandmarks()
          .withFaceDescriptors()
          .withFaceExpressions();
        
        const ssdTime = performance.now() - ssdStartTime;
        console.log(`🐌 SSD MobileNet (Multiple): ${ssdTime.toFixed(1)}ms → ${ssdDetections.length} faces`);
        
        // Use whichever found more faces
        if (ssdDetections.length > detections.length) {
          detections = ssdDetections;
          modelUsed = 'SSD MobileNet';
          this.performanceStats.modelUsage.ssd++;
          console.log('📈 SSD MobileNet found more faces, using those results');
        } else {
          modelUsed = 'TinyFaceDetector';
          this.performanceStats.modelUsage.tiny++;
        }
      } else {
        modelUsed = 'TinyFaceDetector';
        this.performanceStats.modelUsage.tiny++;
      }

      const totalTime = performance.now() - startTime;
      this.performanceStats.detectionTimes.push(totalTime);

      console.log(`✅ Detected ${detections.length} faces using ${modelUsed} in ${totalTime.toFixed(1)}ms`);
      
      // Log quality metrics for each face
      detections.forEach((detection, i) => {
        const descriptorSum = detection.descriptor.reduce((sum, val) => sum + Math.abs(val), 0);
        console.log(`Face ${i + 1}: confidence=${detection.detection.score.toFixed(3)}, quality=${descriptorSum.toFixed(3)}`);
      });

      // Log performance stats periodically
      if (this.performanceStats.detectionTimes.length % 5 === 0) {
        this.logPerformanceStats();
      }

      return detections;
    } catch (error) {
      console.error('Error detecting faces:', error);
      return [];
    }
  }

  compareFaces(descriptor1: Float32Array, descriptor2: Float32Array): number {
    // Validate descriptors
    if (!descriptor1 || !descriptor2 || descriptor1.length !== 128 || descriptor2.length !== 128) {
      console.error('Invalid face descriptors for comparison');
      return 0;
    }

    const distance = faceapi.euclideanDistance(descriptor1, descriptor2);
    
    // Optimized similarity calculation based on FaceNet research
    // Same person typically: 0.2-0.6 distance
    // Different people typically: 0.8-1.2+ distance
    let similarity;
    
    if (distance < 0.3) {
      // Excellent match - same person, good conditions
      similarity = 0.99 - (distance * 0.3); // 99% to 90%
    } else if (distance < 0.5) {
      // Very good match - same person, different conditions
      similarity = 0.90 - ((distance - 0.3) * 2); // 90% to 50%
    } else if (distance < 0.7) {
      // Good match - likely same person
      similarity = 0.50 - ((distance - 0.5) * 1.5); // 50% to 20%
    } else if (distance < 1.0) {
      // Poor match - likely different person
      similarity = 0.20 - ((distance - 0.7) * 0.5); // 20% to 5%
    } else {
      // Very poor match - definitely different person
      similarity = Math.max(0.01, 0.05 - ((distance - 1.0) * 0.04)); // 5% to 1%
    }
    
    // Ensure similarity is between 0 and 1
    similarity = Math.max(0, Math.min(1, similarity));
    
    console.log(`🔍 Distance: ${distance.toFixed(4)} → Similarity: ${(similarity * 100).toFixed(2)}%`);
    
    // Add quality indicators
    if (similarity > 0.95) {
      console.log('🎯 Excellent match!');
    } else if (similarity > 0.80) {
      console.log('✅ Very good match');
    } else if (similarity > 0.60) {
      console.log('👍 Good match');
    } else if (similarity > 0.40) {
      console.log('⚠️ Weak match');
    } else {
      console.log('❌ Poor match');
    }
    
    return similarity;
  }

  getEmotion(expressions: faceapi.FaceExpressions): { emotion: string; confidence: number } {
    const emotions = expressions.asSortedArray();
    const topEmotion = emotions[0];
    
    console.log(`🎭 Detected emotions:`, emotions.map(e => `${e.expression}: ${(e.probability * 100).toFixed(1)}%`).join(', '));
    console.log(`🎯 Top emotion: ${topEmotion.expression} (${(topEmotion.probability * 100).toFixed(1)}%)`);
    
    return {
      emotion: topEmotion.expression, // Return raw emotion for proper mapping
      confidence: topEmotion.probability
    };
  }

  // Helper to create image element from base64 with preprocessing
  createImageElement(base64Data: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        // Create canvas for image preprocessing
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;
        
        // Set optimal size for face-api.js (larger size for better recognition)
        const targetSize = 640;  // Increased from 512 for better quality
        canvas.width = targetSize;
        canvas.height = targetSize;
        
        // Enable high-quality image smoothing
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        
        // Draw image with proper scaling
        ctx.drawImage(img, 0, 0, targetSize, targetSize);
        
        // Apply slight contrast enhancement for better face detection
        const imageData = ctx.getImageData(0, 0, targetSize, targetSize);
        const data = imageData.data;
        
        // Enhance contrast more for better face recognition
        const contrast = 1.2;  // Increased from 1.1
        const brightness = 8;  // Increased from 5
        
        for (let i = 0; i < data.length; i += 4) {
          // Apply contrast and brightness to RGB channels
          data[i] = Math.min(255, Math.max(0, contrast * (data[i] - 128) + 128 + brightness));     // Red
          data[i + 1] = Math.min(255, Math.max(0, contrast * (data[i + 1] - 128) + 128 + brightness)); // Green
          data[i + 2] = Math.min(255, Math.max(0, contrast * (data[i + 2] - 128) + 128 + brightness)); // Blue
          // Alpha channel stays the same
        }
        
        ctx.putImageData(imageData, 0, 0);
        
        // Create new image from processed canvas
        const processedImg = new Image();
        processedImg.onload = () => {
          console.log(`Image preprocessed: ${targetSize}x${targetSize}, enhanced contrast`);
          resolve(processedImg);
        };
        processedImg.onerror = reject;
        processedImg.src = canvas.toDataURL('image/jpeg', 0.95); // High quality JPEG
      };
      img.onerror = reject;
      img.src = `data:image/jpeg;base64,${base64Data}`;
    });
  }

  // Helper to create original image (for comparison)
  createOriginalImageElement(base64Data: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = `data:image/jpeg;base64,${base64Data}`;
    });
  }

  // Performance monitoring
  private logPerformanceStats() {
    const detectionTimes = this.performanceStats.detectionTimes;
    const avgDetection = detectionTimes.reduce((a, b) => a + b, 0) / detectionTimes.length;
    const minDetection = Math.min(...detectionTimes);
    const maxDetection = Math.max(...detectionTimes);
    
    console.log('📊 PERFORMANCE STATS:');
    console.log(`⚡ Average Detection Time: ${avgDetection.toFixed(1)}ms`);
    console.log(`🚀 Fastest Detection: ${minDetection.toFixed(1)}ms`);
    console.log(`🐌 Slowest Detection: ${maxDetection.toFixed(1)}ms`);
    console.log(`🎯 TinyFaceDetector Usage: ${this.performanceStats.modelUsage.tiny} times`);
    console.log(`📱 SSD MobileNet Usage: ${this.performanceStats.modelUsage.ssd} times`);
    console.log(`⚡ Efficiency: ${((this.performanceStats.modelUsage.tiny / (this.performanceStats.modelUsage.tiny + this.performanceStats.modelUsage.ssd)) * 100).toFixed(1)}% TinyFaceDetector`);
  }

  // Get current performance stats
  getPerformanceStats() {
    const detectionTimes = this.performanceStats.detectionTimes;
    if (detectionTimes.length === 0) return null;
    
    const avgDetection = detectionTimes.reduce((a, b) => a + b, 0) / detectionTimes.length;
    const total = this.performanceStats.modelUsage.tiny + this.performanceStats.modelUsage.ssd;
    
    return {
      averageDetectionTime: avgDetection,
      totalDetections: detectionTimes.length,
      tinyFaceDetectorUsage: this.performanceStats.modelUsage.tiny,
      ssdMobileNetUsage: this.performanceStats.modelUsage.ssd,
      efficiency: total > 0 ? (this.performanceStats.modelUsage.tiny / total) * 100 : 0
    };
  }
}

export const faceApiService = new FaceApiService();
