from flask import Flask, Response, request, jsonify, render_template
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_java_algorithm_stream', methods=['POST','GET'])
def run_java_algorithm_stream():
    # 根据请求获取参数并构造 Java 命令
    estimation = request.json.get('estimation', 'supervised')
    dataset = request.json.get('dataset', 'HCB')
    
    if estimation == "supervised":
        nfold = request.json.get('nfold', 10)
        if nfold > 0:
            supervision_percentage = 100 / nfold
        else:
            supervision_percentage = 100 - (100 / abs(nfold))
        folder_name = "nFoldSet_" + str(supervision_percentage)
        saveDir = f"./nFoldSets/{dataset}/{estimation}/{folder_name}/"
        
        text_content = (
            f"--responses ./data/{dataset}/responses.txt "
            f"--category ./data/{dataset}/categories.txt "
            f"--groundTruth ./data/{dataset}/groundTruth.txt "
            f"--method All --nfold -{nfold} "
            f"--estimation {estimation} --saveDir {saveDir}"
        )
        text_file_name = f"genNFold{nfold}_{dataset}_{estimation}_CLA.txt"
    else:
        saveDir = f"./nFoldSets/{dataset}/{estimation}/"
        text_content = (
            f"--responses ./data/{dataset}/responses.txt "
            f"--category ./data/{dataset}/categories.txt "
            f"--groundTruth ./data/{dataset}/groundTruth.txt "
            f"--method All --estimation {estimation} --saveDir {saveDir}"
        )
        text_file_name = f"gen_{dataset}_{estimation}_CLA.txt"
    
    # 将配置内容写入文件
    with open(text_file_name, "w", encoding="utf-8") as file:
        file.write(text_content)
    print(f"内容已写入 {text_file_name}")

    # 构造 Java 命令
    cmd = [
        'java',
        '-Xmx2048m',
        '-ea',
        '-cp',
        './jblas-1.2.4.jar:./log4j-core-2.4.jar:./log4j-api-2.4.jar:./qa-2.0.jar',
        'org.square.qa.analysis.Main',
        '--file',
        text_file_name
    ]
    
    def generate():
        # 使用 Popen 启动子进程，并逐行读取输出
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            # 每读取一行，构造 SSE 格式的数据
            yield f"data: {line}\n\n"
        process.stdout.close()
        return_code = process.wait()
        yield f"data: Process finished with return code {return_code}\n\n"
    
    # 返回 SSE 流响应
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
