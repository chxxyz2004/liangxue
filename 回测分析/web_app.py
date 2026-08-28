#!/usr/bin/env python3
"""
量学回测分析Web界面
端口: 8087
功能: 回测策略选择、结果可视化、报告生成
"""
import json
import os
import sys
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from urllib.parse import urlparse

sys.path.insert(0, '/workspace/回测分析')
sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/现代量学讲义')

from config import HOLDINGS, WATCH_LIST, INDEXES
from backtest_engine import run_backtest, batch_backtest

app = Flask(__name__)

# 缓存回测结果
_backtest_cache = {}


# ==================== HTML模板 ====================

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>量学回测分析</title>
<style>
:root {
  --bg: #0a0e14;
  --surface: #151b23;
  --surface2: #1e2530;
  --border: #2a3441;
  --text: #e8edf4;
  --text-dim: #8899a6;
  --red: #ff4757;
  --green: #2ed573;
  --blue: #3498db;
  --orange: #e67e22;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", sans-serif; background: var(--bg); color: var(--text); }
a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; }

/* 顶部导航 */
.navbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.navbar h1 { font-size: 18px; font-weight: 600; }
.navbar .back-link { font-size: 14px; color: var(--text-dim); }

/* 主容器 */
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

/* 控制面板 */
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.panel h2 { font-size: 16px; margin-bottom: 15px; color: var(--text); }
.form-row { display: flex; gap: 15px; flex-wrap: wrap; align-items: flex-end; }
.form-group { display: flex; flex-direction: column; gap: 5px; }
.form-group label { font-size: 12px; color: var(--text-dim); }
.form-group select, .form-group input {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
}
.btn {
  background: var(--blue);
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}
.btn:hover { opacity: 0.9; }
.btn-green { background: var(--green); }
.btn-orange { background: var(--orange); }

/* 结果卡片 */
.results-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
.result-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 15px;
}
.result-card h3 { font-size: 14px; color: var(--text-dim); margin-bottom: 10px; }
.result-card .value { font-size: 24px; font-weight: 600; }
.result-card .value.green { color: var(--green); }
.result-card .value.red { color: var(--red); }
.result-card .value.orange { color: var(--orange); }

/* 表格 */
.table-container { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--surface2); color: var(--text-dim); font-weight: 500; }
tr:hover { background: var(--surface2); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.badge-green { background: rgba(46,213,115,0.2); color: var(--green); }
.badge-red { background: rgba(255,71,87,0.2); color: var(--red); }
.badge-orange { background: rgba(230,126,34,0.2); color: var(--orange); }

/* 加载状态 */
.loading { text-align: center; padding: 40px; color: var(--text-dim); }
.loading::after { content: '...'; animation: dots 1.5s infinite; }
@keyframes dots { 0% { content: ''; } 33% { content: '.'; } 66% { content: '..'; } }

/* 图表容器 */
.chart-container { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-top: 15px; }
.chart-container h3 { font-size: 14px; margin-bottom: 10px; }
canvas { max-width: 100%; }
</style>
</head>
<body>

<div class="navbar">
  <a href="http://localhost:8000" class="back-link">← 返回讲义网站</a>
  <h1>量学回测分析</h1>
</div>

<div class="container">
  <!-- 控制面板 -->
  <div class="panel">
    <h2>回测设置</h2>
    <div class="form-row">
      <div class="form-group">
        <label>选择股票</label>
        <select id="stockSelect">
          {% for sym, info in holdings.items() %}
          <option value="{{ sym }}">{{ info.name }} ({{ sym }})</option>
          {% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label>回测策略</label>
        <select id="strategySelect">
          <option value="all">全部策略</option>
          <option value="volume">倍量柱信号</option>
          <option value="golden">黄金线支撑</option>
          <option value="price">支撑压力位</option>
        </select>
      </div>
      <div class="form-group">
        <label>回测周期</label>
        <select id="periodSelect">
          <option value="30">最近30天</option>
          <option value="60" selected>最近60天</option>
          <option value="120">最近120天</option>
          <option value="250">最近250天</option>
        </select>
      </div>
      <button class="btn" onclick="runBacktest()">开始回测</button>
      <button class="btn btn-green" onclick="batchBacktest()">批量回测</button>
    </div>
  </div>

  <!-- 加载提示 -->
  <div id="loading" class="loading" style="display:none;">正在回测分析中</div>

  <!-- 单股结果 -->
  <div id="singleResult" style="display:none;">
    <div class="panel">
      <h2 id="resultTitle">回测结果</h2>
      <div id="resultContent"></div>
    </div>
  </div>

  <!-- 批量结果 -->
  <div id="batchResult" style="display:none;">
    <div class="panel">
      <h2>批量回测结果</h2>
      <div class="table-container" id="batchTable"></div>
    </div>
  </div>
</div>

<script>
async function runBacktest() {
  const symbol = document.getElementById('stockSelect').value;
  const strategy = document.getElementById('strategySelect').value;
  const period = document.getElementById('periodSelect').value;
  
  document.getElementById('loading').style.display = 'block';
  document.getElementById('singleResult').style.display = 'none';
  document.getElementById('batchResult').style.display = 'none';
  
  const resp = await fetch(`/api/backtest?symbol=${symbol}&strategy=${strategy}&period=${period}`);
  const data = await resp.json();
  
  document.getElementById('loading').style.display = 'none';
  
  if (data.error) {
    alert(data.error);
    return;
  }
  
  document.getElementById('resultTitle').textContent = `${data.name} (${symbol}) 回测结果`;
  document.getElementById('singleResult').style.display = 'block';
  
  let html = '<div class="results-grid">';
  
  // 总体信息
  html += `<div class="result-card"><h3>数据范围</h3><div class="value">${data.date_range}</div></div>`;
  html += `<div class="result-card"><h3>总交易日</h3><div class="value">${data.total_days}</div></div>`;
  
  // 各策略结果
  const strategies = data.strategies || {};
  
  if (strategies.volume) {
    const s = strategies.volume;
    html += `<div class="result-card"><h3>倍量柱信号</h3><div class="value green">${s.count}次</div></div>`;
    if (s.signals && s.signals.length > 0) {
      html += `<div style="margin-top:15px"><h3>最近信号</h3><table><tr><th>日期</th><th>类型</th><th>量比</th><th>收盘价</th><th>涨幅</th></tr>`;
      s.signals.slice(-5).reverse().forEach(sig => {
        html += `<tr><td>${sig.date}</td><td><span class="badge badge-orange">${sig.type}</span></td><td>${sig.volume_ratio}x</td><td>${sig.price}</td><td>${sig.change_pct}%</td></tr>`;
      });
      html += '</table></div>';
    }
  }
  
  if (strategies.golden_line) {
    const s = strategies.golden_line;
    html += `<div class="result-card"><h3>黄金线支撑</h3><div class="value ${s.win_rate >= 50 ? 'green' : 'red'}">${s.win_rate}%</div><div style="font-size:12px;color:var(--text-dim)">${s.total}次测试 | 有效${s.valid}次 失效${s.invalid}次</div></div>`;
  }
  
  if (strategies.price_level) {
    const s = strategies.price_level;
    html += `<div class="result-card"><h3>支撑压力位</h3><div class="value ${s.win_rate >= 50 ? 'green' : 'red'}">${s.win_rate}%</div><div style="font-size:12px;color:var(--text-dim)">${s.total}次测试 | 有效${s.valid}次 失效${s.invalid}次</div></div>`;
  }
  
  html += '</div>';
  
  // 详细结果
  if (strategies.golden_line && strategies.golden_line.hits && strategies.golden_line.hits.length > 0) {
    html += '<div class="chart-container"><h3>黄金线支撑测试详情</h3><div class="table-container"><table><tr><th>日期</th><th>支撑位</th><th>结果</th></tr>';
    strategies.golden_line.hits.slice(-10).reverse().forEach(hit => {
      const cls = hit.outcome === '有效' ? 'badge-green' : 'badge-red';
      html += `<tr><td>${hit.date}</td><td>${hit.support}</td><td><span class="badge ${cls}">${hit.outcome}</span></td></tr>`;
    });
    html += '</table></div></div>';
  }
  
  document.getElementById('resultContent').innerHTML = html;
}

async function batchBacktest() {
  const strategy = document.getElementById('strategySelect').value;
  
  document.getElementById('loading').style.display = 'block';
  document.getElementById('singleResult').style.display = 'none';
  document.getElementById('batchResult').style.display = 'none';
  
  const resp = await fetch(`/api/batch_backtest?strategy=${strategy}`);
  const data = await resp.json();
  
  document.getElementById('loading').style.display = 'none';
  
  if (data.error) {
    alert(data.error);
    return;
  }
  
  document.getElementById('batchResult').style.display = 'block';
  
  let html = '<table><tr><th>股票代码</th><th>名称</th><th>数据天数</th><th>倍量柱次数</th><th>黄金线胜率</th><th>支撑压力胜率</th></tr>';
  
  for (const [sym, result] of Object.entries(data)) {
    if (result.error) continue;
    const strategies = result.strategies || {};
    const vol = strategies.volume ? strategies.volume.count : '-';
    const golden = strategies.golden_line ? strategies.golden_line.win_rate + '%' : '-';
    const price = strategies.price_level ? strategies.price_level.win_rate + '%' : '-';
    html += `<tr><td>${sym}</td><td>${result.name}</td><td>${result.total_days}</td><td>${vol}</td><td>${golden}</td><td>${price}</td></tr>`;
  }
  
  html += '</table>';
  document.getElementById('batchTable').innerHTML = html;
}

// 页面加载时自动运行一次
window.onload = function() {
  // 不自动运行，等用户点击
};
</script>

</body>
</html>
'''


@app.route('/')
def index():
    """主页"""
    return render_template_string(BASE_TEMPLATE, holdings=HOLDINGS)


@app.route('/api/backtest')
def api_backtest():
    """单股回测API"""
    symbol = request.args.get('symbol', 'sh603516')
    strategy = request.args.get('strategy', 'all')
    period = request.args.get('period', '60')
    
    # 临时修改lookback
    from backtest_engine import run_backtest
    import backtest_engine as be
    
    # 根据period调整lookback
    original_lookback = be.__dict__.get('_last_lookback', 60)
    
    result = run_backtest(symbol, strategy)
    return jsonify(result)


@app.route('/api/batch_backtest')
def api_batch_backtest():
    """批量回测API"""
    strategy = request.args.get('strategy', 'all')
    
    from backtest_engine import batch_backtest
    results = batch_backtest(list(HOLDINGS.keys()), strategy)
    return jsonify(results)


@app.route('/reports')
def reports():
    """报告浏览页"""
    report_dir = '/workspace/现代量学讲义'
    reports = []
    
    for f in sorted(os.listdir(report_dir), reverse=True):
        if f.endswith('.html') and not f.startswith('第') and not f.startswith('作业') and not f.startswith('测验') and not f.startswith('强化') and not f.startswith('方法课'):
            path = os.path.join(report_dir, f)
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')
            reports.append({'name': f, 'size': size, 'date': mtime})
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>报告浏览</title>
<style>
:root { --bg: #0a0e14; --surface: #151b23; --border: #2a3441; --text: #e8edf4; --text-dim: #8899a6; --blue: #3498db; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", sans-serif; background: var(--bg); color: var(--text); }
a { color: var(--blue); text-decoration: none; }
.navbar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 20px; display: flex; align-items: center; gap: 20px; }
.container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--text-dim); font-weight: 500; }
tr:hover { background: var(--surface2); }
</style>
</head>
<body>
<div class="navbar">
  <a href="http://localhost:8000" style="color:var(--text-dim)">← 返回讲义网站</a>
  <h1>历史报告浏览</h1>
</div>
<div class="container">
  <div class="panel">
    <table>
      <tr><th>报告名称</th><th>日期</th><th>大小</th><th>操作</th></tr>
      {% for r in reports %}
      <tr>
        <td>{{ r.name }}</td>
        <td>{{ r.date }}</td>
        <td>{{ "%.1f"|format(r.size/1024) }} KB</td>
        <td><a href="/reports/{{ r.name }}">查看</a></td>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>
</body>
</html>
''', reports=reports)


@app.route('/reports/<filename>')
def view_report(filename):
    """查看报告"""
    path = f'/workspace/现代量学讲义/{filename}'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return '报告不存在', 404


@app.route('/backtest_reports')
def backtest_reports():
    """回测报告浏览"""
    report_dir = '/workspace/回测分析/reports'
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
        reports = []
    else:
        reports = []
        for f in sorted(os.listdir(report_dir), reverse=True):
            if f.endswith('.json'):
                path = os.path.join(report_dir, f)
                reports.append({'name': f, 'size': os.path.getsize(path)})
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>回测报告</title>
<style>
:root { --bg: #0a0e14; --surface: #151b23; --border: #2a3441; --text: #e8edf4; --text-dim: #8899a6; --blue: #3498db; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", sans-serif; background: var(--bg); color: var(--text); }
a { color: var(--blue); text-decoration: none; }
.navbar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 20px; display: flex; align-items: center; gap: 20px; }
.container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--text-dim); font-weight: 500; }
</style>
</head>
<body>
<div class="navbar">
  <a href="/" style="color:var(--text-dim)">← 回测首页</a>
  <h1>回测报告历史</h1>
</div>
<div class="container">
  <div class="panel">
    <table>
      <tr><th>报告名称</th><th>大小</th><th>操作</th></tr>
      {% for r in reports %}
      <tr>
        <td>{{ r.name }}</td>
        <td>{{ "%.1f"|format(r.size/1024) }} KB</td>
        <td><a href="/backtest_reports/{{ r.name }}">查看</a></td>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>
</body>
</html>
''', reports=reports)


@app.route('/backtest_reports/<filename>')
def view_backtest_report(filename):
    """查看回测报告"""
    path = f'/workspace/回测分析/reports/{filename}'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return '报告不存在', 404




@app.route('/preplan')
def preplan_page():
    """盘前预案页"""
    with open('/workspace/现代量学讲义/盘前预案.md', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/review')
def review_page():
    """复盘日报页"""
    with open('/workspace/现代量学讲义/复盘日报.md', 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8087
    print(f'量学回测分析系统启动: http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
