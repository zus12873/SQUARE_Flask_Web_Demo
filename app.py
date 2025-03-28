import os
from flask import Flask, Response, request, jsonify, render_template
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run_java_algorithm_stream', methods=['GET', 'POST'])
def run_java_algorithm_stream():
    # 获取前端传入的参数（POST 的 JSON数据；GET时使用默认值）
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
    else:
        data = {}
    # 获取参数
    estimation = data.get('estimation', 'supervised')
    dataset = data.get('dataset', 'HCB')
    nfold = data.get('nfold', 10)

    # 根据监督方式构造配置文件及保存目录
    if estimation == "supervised":
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

    # 构造 Java 命令，注意根据你的 jar 路径调整
    cmd = [
        'java',
        '-Xmx2048m',
        '-ea',
        '-cp',
        './algorithm/jblas-1.2.4.jar:./algorithm/log4j-core-2.4.jar:./algorithm/log4j-api-2.4.jar:./algorithm/qa-2.0.jar',
        'org.square.qa.analysis.Main',
        '--file',
        text_file_name
    ]
    
    def generate():
        # 启动 Java 进程，并实时输出日志
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line}\n\n"
        process.stdout.close()
        return_code = process.wait()
        yield f"data: Process finished with return code {return_code}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/get_evaluation_results', methods=['POST'])
def get_evaluation_results():
    """
    该接口根据前端传入的参数读取结果文件夹下所有 .txt 文件，
    提取文件名中的评分方法，并解析文件内容，将数据打包成 JSON 返回给前端。
    """
    data = request.get_json() or {}
    estimation = data.get('estimation', 'supervised')
    dataset = data.get('dataset', 'HCB')
    nfold = data.get('nfold', 10)
    
    # 构造结果文件夹路径
    if estimation == "supervised":
        if nfold > 0:
            supervision_percentage = 100 / nfold
        else:
            supervision_percentage = 100 - (100 / abs(nfold))
        results_folder = f"./nFoldSets/{dataset}/{estimation}/nFoldSet_{supervision_percentage}/results/nFold"
    else:
        results_folder = f"./nFoldSets/{dataset}/{estimation}/results/nFold"
    
    results = []
    if os.path.exists(results_folder):
        for filename in os.listdir(results_folder):
            if filename.endswith('.txt'):
                # 提取文件名中评分方法部分（例如 "Majority_unsupervised_results.txt" 提取 "Majority"）
                method = filename.split('_')[0]
                file_path = os.path.join(results_folder, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = [line.strip() for line in f if line.strip()]
                        # 分别获取以 "%" 开头的 header 行和其它数据行
                        headers = [line for line in lines if line.startswith('%')]
                        data_lines = [line for line in lines if not line.startswith('%')]
                    results.append({
                        "method": method,
                        "filename": filename,
                        "headers": headers,
                        "data": data_lines
                    })
                except Exception as e:
                    results.append({
                        "method": method,
                        "filename": filename,
                        "error": str(e)
                    })
        return jsonify({"results": results})
    else:
        return jsonify({"error": f"Results folder {results_folder} does not exist"}), 404

if __name__ == '__main__':
    app.run(debug=True)
