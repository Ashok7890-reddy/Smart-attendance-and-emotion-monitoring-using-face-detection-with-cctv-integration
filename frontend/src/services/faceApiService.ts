import * as faceapi from 'face-api.js';

export class FaceApiService {
  private modelsLoaded = false;
  private loadingPromise: Promise<void> | null = null;

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
      
      console.log('Loading face-api.js models from:', MODEL_URL);
      console.log('Current URL:', window.location.href);
      
      // Load models one by one with better error handling
      console.log('Loading SSD MobileNet v1...');
      await faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL);
      console.log('✅ SSD MobileNet v1 loaded');
      
      console.log('Loading Face Landmark 68...');
      await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
      console.log('✅ Face Landmark 68 loaded');
      
      console.log('Loading Face Recognition...');
      await faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
      console.log('✅ Face Recognition loaded');
      
      console.log('Loading Face Expression...');
      await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);
      console.log('✅ Face Expression loaded');
      
      this.modelsLoaded = true;
      console.log('✅ All face-api.js models loaded successfully!');
    } catch (error) {
      console.error('❌ Error loading face-api models:', error);
      console.error('Error details:', error);
      throw new Error(`Failed to load face recognition models: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async detectFace(imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement) {
    await this.loadModels();

    try {
      const detection = await faceapi
        .detectSingleFace(imageElement, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 }))
        .withFaceLandmarks()
        .withFaceDescriptor()
        .withFaceExpressions();

      return detection;
    } catch (error) {
      console.error('Error detecting face:', error);
      return null;
    }
  }

  async detectMultipleFaces(imageElement: HTMLImageElement | HTMLVideoElement | HTMLCanvasElement) {
    await this.loadModels();

    try {
      const detections = await faceapi
        .detectAllFaces(imageElement, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 }))
        .withFaceLandmarks()
        .withFaceDescriptors()
        .withFaceExpressions();

      return detections;
    } catch (error) {
      console.error('Error detecting faces:', error);
      return [];
    }
  }

  compareFaces(descriptor1: Float32Array, descriptor2: Float32Array): number {
    const distance = faceapi.euclideanDistance(descriptor1, descriptor2);
    // Convert distance to similarity (0-1, where 1 is identical)
    const similarity = 1 / (1 + distance);
    return similarity;
  }

  getEmotion(expressions: faceapi.FaceExpressions): { emotion: string; confidence: number } {
    const emotions = expressions.asSortedArray();
    const topEmotion = emotions[0];
    
    // Map to our categories
    const emotionMap: Record<string, string> = {
      'happy': 'interested',
      'neutral': 'interested',
      'surprised': 'interested',
      'sad': 'bored',
      'angry': 'confused',
      'fearful': 'confused',
      'disgusted': 'bored'
    };
    
    return {
      emotion: emotionMap[topEmotion.expression] || 'interested',
      confidence: topEmotion.probability
    };
  }

  // Helper to create image element from base64
  createImageElement(base64Data: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = `data:image/jpeg;base64,${base64Data}`;
    });
  }
}

export const faceApiService = new FaceApiService();
