from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/run_java_algorithm', methods=['POST'])
def run_java():
    # 获取请求中的文件名参数，如果没有传则使用默认文件 genNFoldRealData_CLA.txt
    
    
    
    file_name = request.json.get('file', 'genNFoldRealData_CLA.txt')
    # 构造 Java 命令
    cmd = [
        'java',
        '-Xmx2048m',
        '-ea',
        '-cp',
        './jblas-1.2.4.jar:./log4j-core-2.4.jar:./log4j-api-2.4.jar:./qa-2.0.jar',
        'org.square.qa.analysis.Main',
        '--file',
        file_name
    ]
    
    try:
        # 执行命令，并捕获标准输出和标准错误
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.CalledProcessError as e:
        # 当命令执行出错时，返回错误信息和返回码
        return jsonify({
            'error': str(e),
            'stdout': e.stdout,
            'stderr': e.stderr,
            'returncode': e.returncode
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
