from flask import Flask, request, send_file, jsonify
from spire.doc import Document, FileFormat
import os
import uuid
import logging
import time
from pathlib import Path
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import threading
import shutil
from datetime import datetime, timedelta

app = Flask(__name__)
# 支持反向代理
app.wsgi_app = ProxyFix(app.wsgi_app)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# 配置常量
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / 'temp'
OUTPUT_DIR = BASE_DIR / 'output'
CACHE_DIR = BASE_DIR / 'cache'
FILE_RETENTION_DAYS = 1  # 文件保留天数
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB
REQUEST_LIMIT = {'count': 0, 'last_reset': time.time(), 'max_per_minute': 60}

# 确保目录存在
for directory in [TEMP_DIR, OUTPUT_DIR, CACHE_DIR]:
    directory.mkdir(exist_ok=True)


# 限流装饰器
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_time = time.time()
        # 每分钟重置计数器
        if current_time - REQUEST_LIMIT['last_reset'] > 60:
            REQUEST_LIMIT['count'] = 0
            REQUEST_LIMIT['last_reset'] = current_time

        if REQUEST_LIMIT['count'] >= REQUEST_LIMIT['max_per_minute']:
            return jsonify(error='Too many requests, please try again later'), 429

        REQUEST_LIMIT['count'] += 1
        return f(*args, **kwargs)

    return decorated_function


# 缓存检查函数
def check_cache(content):
    """检查内容是否已经转换过，如果有则返回缓存文件路径"""
    import hashlib
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    cache_file = CACHE_DIR / f"{content_hash}.docx"

    if cache_file.exists():
        # 复制到输出目录并返回新文件ID
        file_id = uuid.uuid4().hex
        output_file = OUTPUT_DIR / f"{file_id}.docx"
        shutil.copy(cache_file, output_file)
        return file_id

    return None


# 异步转换函数
def convert_async(content, file_id, response_callback=None):
    """异步执行文档转换"""
    try:
        md_path = TEMP_DIR / f"{file_id}.md"
        docx_path = OUTPUT_DIR / f"{file_id}.docx"

        # 写入临时文件
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 计算内容哈希用于缓存
        import hashlib
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        cache_file = CACHE_DIR / f"{content_hash}.docx"

        # 文档转换
        doc = Document()
        doc.LoadFromFile(str(md_path), FileFormat.Markdown)
        doc.SaveToFile(str(docx_path), FileFormat.Docx)

        # 保存到缓存
        if not cache_file.exists():
            doc.SaveToFile(str(cache_file), FileFormat.Docx)

        doc.Dispose()

        # 清理临时文件
        if md_path.exists():
            md_path.unlink()

        logger.info(f"Conversion completed for file: {file_id}")

        if response_callback:
            response_callback(True, file_id)
    except Exception as e:
        logger.error(f"Async conversion failed: {str(e)}")
        if response_callback:
            response_callback(False, str(e))


# 定期清理过期文件
def cleanup_old_files():
    """清理超过保留期限的文件"""
    try:
        cutoff_date = datetime.now() - timedelta(days=FILE_RETENTION_DAYS)

        # 清理输出目录
        for file_path in OUTPUT_DIR.glob('*.docx'):
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                file_path.unlink()
                logger.info(f"Deleted old output file: {file_path}")

        # 清理临时目录
        for file_path in TEMP_DIR.glob('*.*'):
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                file_path.unlink()
                logger.info(f"Deleted old temp file: {file_path}")
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")


# 启动定期清理任务
def start_cleanup_scheduler():
    """启动定期清理任务"""
    cleanup_old_files()
    # 每天运行一次清理
    threading.Timer(86400, start_cleanup_scheduler).start()


# 启动清理任务
start_cleanup_scheduler()


@app.route('/convert', methods=['POST'])
@rate_limit
def convert_md_to_docx():
    """Convert Markdown content to DOCX document"""
    try:
        logger.info('Received request for /convert')

        # 验证请求内容
        if not request.data:
            logger.warning('No content provided')
            return jsonify(error='No content provided'), 400

        content = request.data.decode('utf-8').strip()
        if not content:
            logger.warning('Empty content')
            return jsonify(error='Empty content'), 400

        # 检查内容大小
        if len(content) > MAX_CONTENT_SIZE:
            logger.warning(f'Content too large: {len(content)} bytes')
            return jsonify(error='Content too large, maximum size is 10MB'), 413

        # 检查缓存
        cached_file_id = check_cache(content)
        if cached_file_id:
            logger.info(f'Cache hit, returning cached file: {cached_file_id}')
            download_url = request.host_url + f'download/{cached_file_id}.docx'
            return jsonify(download_url=download_url)

        # 生成唯一文件名
        file_id = uuid.uuid4().hex

        # 对于小文件，同步处理
        if len(content) < 100 * 1024:  # 小于100KB
            md_path = TEMP_DIR / f"{file_id}.md"
            docx_path = OUTPUT_DIR / f"{file_id}.docx"

            # 写入临时文件
            try:
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except IOError as e:
                logger.error(f'File write error: {str(e)}')
                return jsonify(error='File processing failed'), 500

            # 文档转换
            try:
                doc = Document()
                doc.LoadFromFile(str(md_path), FileFormat.Markdown)
                doc.SaveToFile(str(docx_path), FileFormat.Docx)

                # 保存到缓存
                import hashlib
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                cache_file = CACHE_DIR / f"{content_hash}.docx"
                if not cache_file.exists():
                    doc.SaveToFile(str(cache_file), FileFormat.Docx)

                doc.Dispose()
            except Exception as e:
                logger.error(f'Conversion failed: {str(e)}')
                return jsonify(error='Document conversion failed'), 500
            finally:
                # 清理临时文件
                if md_path.exists():
                    md_path.unlink()
        else:
            # 对于大文件，异步处理
            threading.Thread(
                target=convert_async,
                args=(content, file_id)
            ).start()

        # 生成下载链接
        download_url = request.host_url + f'download/{file_id}.docx'
        return jsonify(download_url=download_url)

    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return jsonify(error='Internal server error'), 500


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download converted DOCX file"""
    try:
        # 防止路径遍历
        if '..' in filename or filename.startswith('/'):
            logger.warning(f'Invalid filename requested: {filename}')
            return jsonify(error='Invalid filename'), 400

        file_path = OUTPUT_DIR / filename

        # 等待文件生成完成（最多等待30秒）
        wait_time = 0
        while not file_path.exists() and wait_time < 30:
            time.sleep(0.5)
            wait_time += 0.5

        if not file_path.exists():
            logger.warning(f'File not found: {filename}')
            return jsonify(error='File not found or conversion still in progress'), 404

        # 更新文件访问时间以防止过早清理
        os.utime(file_path, None)

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f'Download failed: {str(e)}')
        return jsonify(error='File download failed'), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify(status='ok', version='1.0.0')


if __name__ == '__main__':
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5009)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
