import json
import random
import os
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# 飞书API基础URL
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 配置
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', 'cli_a9475f00d17c5cd5')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', '')
BITABLE_APP_TOKEN = os.environ.get('BITABLE_APP_TOKEN', 'J6qkbf7jaaGPIys07AocdDBsnTc')
QUESTION_TABLE_ID = os.environ.get('QUESTION_TABLE_ID', 'tblmwn04El1RDgn0')
RECORD_TABLE_ID = os.environ.get('RECORD_TABLE_ID', 'tblgM69XeweluqbQ')
QUESTIONS_PER_SESSION = int(os.environ.get('QUESTIONS_PER_SESSION', 5))

# 内存中存储用户答题状态（Vercel是serverless，建议使用Redis或数据库持久化）
user_sessions = {}

# 读取卡片模板
CARD_TEMPLATE = {
    "schema": "2.0",
    "config": {"update_multi": True},
    "body": {
        "direction": "vertical",
        "elements": [
            {
                "tag": "markdown",
                "content": "**${title}**",
                "text_align": "left",
                "text_size": "normal",
                "margin": "0px 0px 0px 0px"
            },
            {
                "tag": "column_set",
                "flex_mode": "stretch",
                "horizontal_spacing": "8px",
                "horizontal_align": "left",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "elements": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "A. ${option_a}"},
                                "type": "default",
                                "width": "fill",
                                "size": "tiny",
                                "behaviors": [{"type": "callback", "value": {"action": "select_answer", "answer": "A"}}],
                                "margin": "4px 0px 4px 0px"
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "B. ${option_b}"},
                                "type": "default",
                                "width": "fill",
                                "size": "tiny",
                                "behaviors": [{"type": "callback", "value": {"action": "select_answer", "answer": "B"}}],
                                "margin": "4px 0px 4px 0px"
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "C. ${option_c}"},
                                "type": "default",
                                "width": "fill",
                                "size": "tiny",
                                "behaviors": [{"type": "callback", "value": {"action": "select_answer", "answer": "C"}}],
                                "margin": "4px 0px 4px 0px"
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "D. ${option_d}"},
                                "type": "default",
                                "width": "fill",
                                "size": "tiny",
                                "behaviors": [{"type": "callback", "value": {"action": "select_answer", "answer": "D"}}],
                                "margin": "4px 0px 4px 0px"
                            }
                        ],
                        "direction": "vertical",
                        "weight": 1
                    }
                ],
                "margin": "0px 0px 0px 0px"
            },
            {
                "tag": "markdown",
                "content": "**答案解析：** ${analysis}",
                "text_align": "left",
                "text_size": "normal",
                "margin": "0px 0px 0px 0px"
            },
            {
                "tag": "markdown",
                "content": "**<font color=\"blue\">本次得分：${score}分</font>**",
                "text_align": "left",
                "text_size": "normal",
                "margin": "0px 0px 0px 0px"
            }
        ]
    }
}


def get_tenant_access_token():
    """获取飞书租户访问令牌"""
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("tenant_access_token")
    except Exception as e:
        print(f"Get token error: {e}")
    return None


def get_user_info(user_open_id, token):
    """获取用户信息"""
    url = f"{FEISHU_API_BASE}/contact/v3/users/{user_open_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", {})
            return {
                "name": data.get("name", ""),
                "department": data.get("department_ids", [""])[0] if data.get("department_ids") else ""
            }
    except Exception as e:
        print(f"Get user info error: {e}")
    return {"name": "", "department": ""}


def get_all_questions(token):
    """获取所有题目"""
    url = f"{FEISHU_API_BASE}/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{QUESTION_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    all_records = []
    has_more = True
    page_token = None
    
    try:
        while has_more and len(all_records) < 500:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json().get("data", {})
                all_records.extend(data.get("items", []))
                has_more = data.get("has_more", False)
                page_token = data.get("page_token")
            else:
                break
    except Exception as e:
        print(f"Get questions error: {e}")
    
    return all_records


def parse_question(record):
    """解析题目数据"""
    fields = record.get("fields", {})
    
    def get_text(field):
        if isinstance(field, list) and len(field) > 0:
            return field[0].get("text", "")
        return str(field) if field else ""
    
    return {
        "record_id": record.get("record_id"),
        "question_no": fields.get("题号", 0),
        "content": get_text(fields.get("题目内容")),
        "option_a": get_text(fields.get("选项A")),
        "option_b": get_text(fields.get("选项B")),
        "option_c": get_text(fields.get("选项C")),
        "option_d": get_text(fields.get("选项D")),
        "correct_answer": get_text(fields.get("正确答案")),
        "analysis": get_text(fields.get("答案解析")),
        "score": fields.get("分值", 0),
        "difficulty": fields.get("难度", "")
    }


def save_answer_record(token, user_info, question, user_answer, is_correct, score_earned, session_id):
    """保存答题记录到多维表格"""
    url = f"{FEISHU_API_BASE}/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{RECORD_TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    data = {
        "fields": {
            "用户ID": user_info.get("open_id", ""),
            "用户姓名": user_info.get("name", ""),
            "部门": user_info.get("department", ""),
            "题号": question["question_no"],
            "题目内容": question["content"],
            "用户答案": user_answer,
            "正确答案": question["correct_answer"],
            "是否正确": "是" if is_correct else "否",
            "分值": question["score"],
            "获得分数": score_earned,
            "答题时间": current_time,
            "答题批次": session_id
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Save record error: {e}")
    return False


def send_message(token, user_open_id, content, msg_type="text"):
    """发送消息"""
    url = f"{FEISHU_API_BASE}/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"receive_id_type": "open_id"}
    
    if msg_type == "text":
        data = {
            "receive_id": user_open_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }
    else:
        data = {
            "receive_id": user_open_id,
            "msg_type": "interactive",
            "content": json.dumps(content)
        }
    
    try:
        response = requests.post(url, headers=headers, params=params, json=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {}).get("message_id")
    except Exception as e:
        print(f"Send message error: {e}")
    return None


def build_question_card(question, current_index, total, show_answer=False, user_answer=None):
    """构建题目卡片"""
    card = json.loads(json.dumps(CARD_TEMPLATE))
    
    title = f"{current_index + 1}. {question['content']}"
    
    card_str = json.dumps(card)
    card_str = card_str.replace('${title}', title)
    card_str = card_str.replace('${option_a}', question['option_a'])
    card_str = card_str.replace('${option_b}', question['option_b'])
    card_str = card_str.replace('${option_c}', question['option_c'])
    card_str = card_str.replace('${option_d}', question['option_d'])
    
    if show_answer:
        analysis = f"{question['analysis']}所以正确答案是{question['correct_answer']}"
        card_str = card_str.replace('${analysis}', analysis)
        
        is_correct = user_answer == question['correct_answer']
        score_earned = question['score'] if is_correct else 0
        card_str = card_str.replace('${score}', str(score_earned))
        
        card_data = json.loads(card_str)
        
        result_text = "✅ 回答正确！" if is_correct else f"❌ 回答错误，正确答案是 {question['correct_answer']}"
        result_element = {
            "tag": "markdown",
            "content": f"**{result_text}**",
            "text_align": "center",
            "text_size": "normal",
            "margin": "0px 0px 10px 0px"
        }
        card_data["body"]["elements"].insert(0, result_element)
        
        if current_index < total - 1:
            next_button = {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "下一题 →"},
                "type": "primary",
                "width": "fill",
                "size": "medium",
                "behaviors": [{"type": "callback", "value": {"action": "next_question"}}],
                "margin": "10px 0px 0px 0px"
            }
            card_data["body"]["elements"].append(next_button)
        else:
            finish_button = {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看结果 🎉"},
                "type": "primary",
                "width": "fill",
                "size": "medium",
                "behaviors": [{"type": "callback", "value": {"action": "finish_quiz"}}],
                "margin": "10px 0px 0px 0px"
            }
            card_data["body"]["elements"].append(finish_button)
        
        return card_data
    else:
        card_str = card_str.replace('${analysis}', "答题后显示")
        card_str = card_str.replace('${score}', "?")
        return json.loads(card_str)


def get_session_summary(token, user_open_id, session_id):
    """获取本次答题统计"""
    url = f"{FEISHU_API_BASE}/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{RECORD_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    filter_data = {
        "conjunction": "and",
        "conditions": [
            {"field_name": "用户ID", "operator": "is", "value": [user_open_id]},
            {"field_name": "答题批次", "operator": "is", "value": [session_id]}
        ]
    }
    
    params = {"filter": json.dumps(filter_data), "page_size": 100}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", {})
            records = data.get("items", [])
            
            total_questions = len(records)
            total_score = sum(r["fields"].get("获得分数", 0) for r in records)
            max_score = sum(r["fields"].get("分值", 0) for r in records)
            
            return {
                "total_questions": total_questions,
                "total_score": total_score,
                "max_score": max_score
            }
    except Exception as e:
        print(f"Get summary error: {e}")
    
    return {"total_questions": 0, "total_score": 0, "max_score": 0}


def handle_event(data):
    """处理飞书事件"""
    event_type = data.get("header", {}).get("event_type")
    
    if event_type == "im.message.receive_v1":
        event_data = data.get("event", {})
        message = event_data.get("message", {})
        sender = event_data.get("sender", {})
        
        user_open_id = sender.get("sender_id", {}).get("open_id")
        
        try:
            msg_content = json.loads(message.get("content", "{}"))
        except:
            return {"code": 0}
        
        text = msg_content.get("text", "").strip()
        
        if "我要答题" in text:
            token = get_tenant_access_token()
            if not token:
                return {"code": 500, "msg": "获取token失败"}
            
            user_info = get_user_info(user_open_id, token)
            user_info["open_id"] = user_open_id
            
            questions_raw = get_all_questions(token)
            if len(questions_raw) < QUESTIONS_PER_SESSION:
                send_message(token, user_open_id, f"题库题目不足，当前仅有{len(questions_raw)}道题")
                return {"code": 0}
            
            selected = random.sample(questions_raw, QUESTIONS_PER_SESSION)
            questions = [parse_question(q) for q in selected]
            
            session_id = f"quiz_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_open_id[:8]}"
            user_sessions[user_open_id] = {
                "session_id": session_id,
                "questions": questions,
                "current_index": 0,
                "answers": [],
                "user_info": user_info
            }
            
            send_message(token, user_open_id, 
                "已为您从题库知识库调取标准化题库，本次答题共5道题，完成作答后将自动判分并计入您的个人考核结果。")
            
            card = build_question_card(questions[0], 0, len(questions), show_answer=False)
            send_message(token, user_open_id, card, msg_type="interactive")
    
    elif event_type == "card.action.trigger":
        return handle_card_callback(data)
    
    return {"code": 0}


def handle_card_callback(data):
    """处理卡片回调"""
    event_data = data.get("event", {})
    action = event_data.get("action", {})
    user_open_id = event_data.get("operator", {}).get("open_id")
    
    action_value = action.get("value", {})
    action_type = action_value.get("action")
    
    token = get_tenant_access_token()
    if not token:
        return {
            "toast": {"type": "error", "content": "系统错误，请重试"}
        }
    
    session = user_sessions.get(user_open_id)
    if not session:
        return {
            "toast": {"type": "error", "content": "答题会话已过期，请重新输入「我要答题」"}
        }
    
    if action_type == "select_answer":
        user_answer = action_value.get("answer")
        current_index = session["current_index"]
        question = session["questions"][current_index]
        
        is_correct = user_answer == question["correct_answer"]
        score_earned = question["score"] if is_correct else 0
        
        save_answer_record(token, session["user_info"], question, 
                          user_answer, is_correct, score_earned, session["session_id"])
        
        session["answers"].append({
            "question_no": question["question_no"],
            "user_answer": user_answer,
            "is_correct": is_correct,
            "score": score_earned
        })
        
        card = build_question_card(question, current_index, 
                                  len(session["questions"]), show_answer=True, user_answer=user_answer)
        
        return {
            "card": card,
            "toast": {
                "type": "success" if is_correct else "error",
                "content": "回答正确！" if is_correct else f"回答错误，正确答案是 {question['correct_answer']}"
            }
        }
    
    elif action_type == "next_question":
        session["current_index"] += 1
        current_index = session["current_index"]
        question = session["questions"][current_index]
        
        card = build_question_card(question, current_index, len(session["questions"]), show_answer=False)
        
        return {"card": card}
    
    elif action_type == "finish_quiz":
        summary = get_session_summary(token, user_open_id, session["session_id"])
        
        result_text = f"""🎉 本次答题已完成！

本次答题共{summary['total_questions']}题，总分{summary['max_score']}分，您的最终得分：{summary['total_score']}分
答题数据已实时同步至飞书多维表格，计入您的个人综合考核结果与数智化指数。"""
        
        if user_open_id in user_sessions:
            del user_sessions[user_open_id]
        
        return {
            "toast": {"type": "success", "content": "答题完成！"},
            "card": {
                "schema": "2.0",
                "body": {
                    "direction": "vertical",
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": result_text,
                            "text_align": "left",
                            "text_size": "normal"
                        }
                    ]
                }
            }
        }
    
    return {"code": 0}


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Handler"""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "message": "Quiz System is running"}).encode())
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            self.send_response(400)
            self.end_headers()
            return
        
        # URL验证挑战
        if data.get("type") == "url_verification":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"challenge": data.get("challenge")}).encode())
            return
        
        # 处理事件
        result = handle_event(data)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
