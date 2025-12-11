# Download Face-API Models

## Option 1: Download from GitHub (Recommended)

Visit: https://github.com/justadudewhohacks/face-api.js/tree/master/weights

Download these files to `frontend/public/models/`:

### Required Models:
1. **ssd_mobilenetv1_model-weights_manifest.json** + shard files
2. **face_landmark_68_model-weights_manifest.json** + shard files  
3. **face_recognition_model-weights_manifest.json** + shard files
4. **face_expression_model-weights_manifest.json** + shard files

## Option 2: Use CDN (Quick Test)

The models will be loaded from CDN automatically if not found locally.

## Option 3: Download Script

Run this in PowerShell:

```powershell
# Create models directory
New-Item -ItemType Directory -Force -Path "frontend/public/models"

# Download models
$baseUrl = "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights"

# List of model files
$models = @(
    "ssd_mobilenetv1_model-weights_manifest.json",
    "ssd_mobilenetv1_model-shard1",
    "face_landmark_68_model-weights_manifest.json",
    "face_landmark_68_model-shard1",
    "face_recognition_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2",
    "face_expression_model-weights_manifest.json",
    "face_expression_model-shard1"
)

foreach ($model in $models) {
    $url = "$baseUrl/$model"
    $output = "frontend/public/models/$model"
    Write-Host "Downloading $model..."
    Invoke-WebRequest -Uri $url -OutFile $output
}

Write-Host "✅ All models downloaded!"
```

## Verification

After downloading, your folder structure should look like:

```
frontend/public/models/
├── ssd_mobilenetv1_model-weights_manifest.json
├── ssd_mobilenetv1_model-shard1
├── face_landmark_68_model-weights_manifest.json
├── face_landmark_68_model-shard1
├── face_recognition_model-weights_manifest.json
├── face_recognition_model-shard1
├── face_recognition_model-shard2
├── face_expression_model-weights_manifest.json
└── face_expression_model-shard1
```

Total size: ~10MB
