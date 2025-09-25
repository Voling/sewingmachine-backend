data "archive_file" "dotenv_layer" {
  type        = "zip"
  source_dir  = "${path.root}/../build/layer"
  output_path = "${path.root}/../build/layer.zip"
}

# Optional local-only layer kept for development. Not attached in prod.

