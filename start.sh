#!/bin/bash
# Motif 一键启动脚本
set -e

cd "$(dirname "$0")"

# 解析参数
LOG_LEVEL="INFO"
if [ "$1" = "--debug" ] || [ "$1" = "-d" ]; then
  LOG_LEVEL="DEBUG"
  echo "🔍 Debug 模式已启用"
fi
export LOG_LEVEL

# 检查 .env 文件
if [ ! -f .env ]; then
  if [ -z "$GOOGLE_GENAI_API_KEY" ]; then
    echo "请先设置 GOOGLE_GENAI_API_KEY:"
    echo "  方式1: cp .env.example .env 然后编辑 .env"
    echo "  方式2: GOOGLE_GENAI_API_KEY=你的key ./start.sh"
    exit 1
  fi
else
  set -a
  source .env
  set +a
fi

cleanup() {
  echo ""
  echo "正在关闭..."
  # 杀主进程及其子进程（uvicorn reloader 会 fork 子进程）
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  pkill -P $BACKEND_PID 2>/dev/null
  pkill -P $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "已关闭"
}
trap cleanup EXIT

# 清理端口上的残留进程
STALE_PIDS=$(lsof -ti :8001 2>/dev/null || true)
if [ -n "$STALE_PIDS" ]; then
  echo "清理端口 8001 上的残留进程..."
  echo "$STALE_PIDS" | xargs kill 2>/dev/null
  sleep 1
fi

# 启动后端
echo "启动后端 (port 8001)..."
source backend/.venv/bin/activate
pip install -q Pillow numpy 2>/dev/null
python -m backend.main &
BACKEND_PID=$!

# 等待后端就绪
echo "等待后端启动..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "后端已就绪"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "后端启动超时，继续启动前端..."
  fi
  sleep 1
done

# 启动前端
echo "启动前端 (port 5173)..."
cd frontend
npx vite &
FRONTEND_PID=$!

echo ""
echo "================================"
echo "  Motif 已启动!"
echo "  打开: http://localhost:5173"
echo "  Ctrl+C 关闭"
echo "================================"
echo ""

wait
