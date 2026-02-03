"""
Storyboard PDF Exporter - Part 1
Episode 1: From beginning to window smashing (inclusive)
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
from datetime import datetime
import os

# Output directory
OUTPUT_DIR = Path(__file__).parent / "pdf_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Register Chinese font
def register_chinese_font():
    """Register Chinese font for PDF"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
            except:
                continue
    return 'Helvetica'

# Storyboard data - Part 1: Beginning to Window Smashing
STORYBOARD_DATA = [
    {
        "shot_number": 1,
        "title": "城市夜景开篇",
        "subject": "城市街道、宁凡",
        "shot_type": "远景转中景 - 夜晚城市街道，霓虹灯闪烁，宁凡骑着电动车穿行",
        "atmosphere": "暖色转冷色、期待中带着不安",
        "environment": "城市夜晚街道，路灯昏黄，车流稀疏",
        "camera_movement": "航拍缓慢下降，跟拍电动车",
        "angle": "高角度俯拍转平视跟拍",
        "special_technique": "航拍转跟拍，建立环境",
        "composition": "远景转中景",
        "style": "电影质感、城市夜景风格",
        "dynamic_control": "电动车在街道上穿行，后座绑着礼品盒",
        "dialogue": "宁凡(内心独白): \"琪琪一定会喜欢这部新手机，攒了三个月工资呢。\""
    },
    {
        "shot_number": 2,
        "title": "宁凡期待表情",
        "subject": "宁凡",
        "shot_type": "近景 - 宁凡骑车时脸上带着温暖的笑意",
        "atmosphere": "暖色、温馨",
        "environment": "街道，背景虚化",
        "camera_movement": "固定跟拍",
        "angle": "侧面近景",
        "special_technique": "浅景深，聚焦表情",
        "composition": "近景",
        "style": "电影质感、暖色调",
        "dynamic_control": "宁凡嘴角带笑，眼神充满期待",
        "dialogue": "无"
    },
    {
        "shot_number": 3,
        "title": "回忆-手机专柜",
        "subject": "宁凡、店员、手机",
        "shot_type": "中景 - 手机专柜，宁凡数着皱巴巴的钞票",
        "atmosphere": "暖色、感动",
        "environment": "明亮的手机专卖店",
        "camera_movement": "第1个宁凡在柜台前，切镜第2个手部数钱特写，切镜第3个店员递手机",
        "angle": "第1个正面中景，第2个手部特写，第3个过肩镜头",
        "special_technique": "切镜、回忆滤镜（胶片质感）",
        "composition": "中景切特写切中景",
        "style": "暖黄色调、胶片质感",
        "dynamic_control": "宁凡小心翼翼数钱，手微微颤抖",
        "dialogue": "店员: \"先生，这是最新款。\"\n宁凡: \"包起来吧。\""
    },
    {
        "shot_number": 4,
        "title": "礼品盒特写",
        "subject": "礼品盒、宁凡的手",
        "shot_type": "特写 - 电动车后座上绑着的礼品盒",
        "atmosphere": "暖色",
        "environment": "电动车后座",
        "camera_movement": "固定，轻微晃动模拟行驶",
        "angle": "俯拍特写",
        "special_technique": "浅景深",
        "composition": "特写",
        "style": "电影质感",
        "dynamic_control": "礼品盒随车身轻微晃动",
        "dialogue": "宁凡(内心独白): \"七年了，从高中到现在，我没让她吃过一点苦...\""
    },
    {
        "shot_number": 5,
        "title": "停车场入口",
        "subject": "宁凡、停车场入口",
        "shot_type": "中景 - 宁凡推着电动车走入昏暗的地下停车场",
        "atmosphere": "暖色转冷色、压抑",
        "environment": "商场地下停车场入口，从明亮转向昏暗",
        "camera_movement": "跟拍宁凡背影进入",
        "angle": "背部跟拍",
        "special_technique": "光线过渡，从暖到冷",
        "composition": "中景",
        "style": "电影质感、冷色调渐变",
        "dynamic_control": "宁凡四处张望寻找妻子的车",
        "dialogue": "宁凡(内心独白): \"她说在商场加班，车应该停在这里...\""
    },
    {
        "shot_number": 6,
        "title": "停车场环境",
        "subject": "停车场内部",
        "shot_type": "远景 - 昏暗的地下停车场全貌，荧光灯闪烁",
        "atmosphere": "冷色、压抑、不安",
        "environment": "地下停车场，混凝土结构，顶部管道和荧光灯",
        "camera_movement": "缓慢横移展示环境",
        "angle": "平视远景",
        "special_technique": "灯光闪烁效果",
        "composition": "远景",
        "style": "电影质感、低饱和度",
        "dynamic_control": "部分灯管闪烁，投下不稳定阴影",
        "dialogue": "无"
    },
    {
        "shot_number": 7,
        "title": "发现异常",
        "subject": "宁凡、远处的保时捷",
        "shot_type": "中景转远景 - 宁凡停下脚步，远处角落一辆保时捷剧烈晃动",
        "atmosphere": "冷色、紧张",
        "environment": "停车场深处，昏暗角落",
        "camera_movement": "第1个宁凡脚步停住，切镜第2个宁凡主观视角看向远处",
        "angle": "第1个侧面中景，第2个主观视角远景",
        "special_technique": "主观镜头、景深变化",
        "composition": "中景切远景",
        "style": "电影质感、冷色调",
        "dynamic_control": "宁凡脚步僵住，保时捷在远处晃动",
        "dialogue": "无"
    },
    {
        "shot_number": 8,
        "title": "保时捷晃动",
        "subject": "保时捷卡宴",
        "shot_type": "中景 - 黑色保时捷卡宴剧烈摇晃，车窗起雾",
        "atmosphere": "冷色、暧昧、压抑",
        "environment": "停车场角落，监控死角",
        "camera_movement": "固定，轻微手持晃动",
        "angle": "侧面中景",
        "special_technique": "车窗起雾效果",
        "composition": "中景",
        "style": "电影质感",
        "dynamic_control": "车身剧烈晃动，车内有暧昧声音",
        "dialogue": "(车内传来声音): \"伟哥...别在这里...\""
    },
    {
        "shot_number": 9,
        "title": "熟悉的发卡",
        "subject": "发卡、宁凡",
        "shot_type": "特写转近景 - 车内后视镜上挂着的发卡，宁凡认出",
        "atmosphere": "冷色、震惊",
        "environment": "保时捷车窗外",
        "camera_movement": "第1个发卡特写，切镜第2个宁凡震惊表情",
        "angle": "第1个发卡特写，第2个宁凡正面近景",
        "special_technique": "切镜、聚焦细节",
        "composition": "特写切近景",
        "style": "电影质感",
        "dynamic_control": "宁凡瞳孔收缩，表情从疑惑到震惊",
        "dialogue": "宁凡(内心独白): \"那个发卡...是我用第一份工资买的...她说会一直戴着...\""
    },
    {
        "shot_number": 10,
        "title": "颤抖靠近",
        "subject": "宁凡",
        "shot_type": "中景 - 宁凡颤抖着一步步靠近保时捷",
        "atmosphere": "冷色、紧张、痛苦",
        "environment": "停车场，从远到近",
        "camera_movement": "缓慢跟拍，镜头轻微晃动",
        "angle": "背部跟拍",
        "special_technique": "手持跟拍，增强不安感",
        "composition": "中景",
        "style": "电影质感、冷色调",
        "dynamic_control": "宁凡脚步沉重，像灌了铅",
        "dialogue": "无"
    },
    {
        "shot_number": 11,
        "title": "透过车窗",
        "subject": "车内纠缠的身影",
        "shot_type": "近景 - 透过起雾的车窗，两个纠缠的身影清晰可辨",
        "atmosphere": "冷色、窒息",
        "environment": "保时捷车窗外视角",
        "camera_movement": "缓慢推进",
        "angle": "宁凡主观视角",
        "special_technique": "起雾效果、主观镜头",
        "composition": "近景",
        "style": "电影质感、朦胧效果",
        "dynamic_control": "车窗后的身影在动",
        "dialogue": "无"
    },
    {
        "shot_number": 12,
        "title": "认出妻子",
        "subject": "杨琪琪、宁凡",
        "shot_type": "特写 - 女人仰起头的瞬间，宁凡看清了那张脸——杨琪琪",
        "atmosphere": "冷色、崩溃",
        "environment": "车窗外",
        "camera_movement": "第1个车内杨琪琪仰头（模糊），切镜第2个宁凡震惊表情大特写",
        "angle": "第1个车内视角，第2个正面大特写",
        "special_technique": "切镜、表情特写",
        "composition": "近景切大特写",
        "style": "电影质感",
        "dynamic_control": "宁凡瞳孔剧烈收缩，整个人僵住",
        "dialogue": "宁凡(声音颤抖): \"琪琪...？\""
    },
    {
        "shot_number": 13,
        "title": "七年回忆闪回-1",
        "subject": "年轻的宁凡和杨琪琪",
        "shot_type": "中景 - 高中教室外，年轻的宁凡递给杨琪琪一本皱巴巴的课本",
        "atmosphere": "暖色、温馨",
        "environment": "高中校园，午后阳光，梧桐树",
        "camera_movement": "固定",
        "angle": "侧面中景",
        "special_technique": "暖黄滤镜、胶片质感",
        "composition": "中景",
        "style": "回忆风格、暖色调",
        "dynamic_control": "阳光透过树叶洒落，两人年轻的笑脸",
        "dialogue": "无"
    },
    {
        "shot_number": 14,
        "title": "七年回忆闪回-2",
        "subject": "宁凡、杨琪琪",
        "shot_type": "中景 - 冬夜街头，宁凡脱下外套披在杨琪琪肩上",
        "atmosphere": "暖色、感动",
        "environment": "冬夜街头，路灯昏黄，雪花飘落",
        "camera_movement": "固定",
        "angle": "侧面中景",
        "special_technique": "暖黄滤镜、雪花效果",
        "composition": "中景",
        "style": "回忆风格",
        "dynamic_control": "宁凡脱下外套，自己只穿单薄毛衣",
        "dialogue": "无"
    },
    {
        "shot_number": 15,
        "title": "七年回忆闪回-3",
        "subject": "宁凡、杨琪琪、结婚证",
        "shot_type": "近景 - 民政局门口，两人手捧红本",
        "atmosphere": "暖色、幸福",
        "environment": "民政局门口，晴天",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "暖黄滤镜、胶片质感",
        "composition": "近景",
        "style": "回忆风格",
        "dynamic_control": "杨琪琪笑着挽着宁凡手臂",
        "dialogue": "杨琪琪(回忆): \"这辈子只嫁你一个。\""
    },
    {
        "shot_number": 16,
        "title": "回到现实-崩溃",
        "subject": "宁凡",
        "shot_type": "大特写 - 宁凡的眼睛，泪水在眼眶打转",
        "atmosphere": "冷色、崩溃",
        "environment": "停车场",
        "camera_movement": "缓慢推进",
        "angle": "正面大特写",
        "special_technique": "从暖色回忆切回冷色现实",
        "composition": "大特写",
        "style": "电影质感、强烈对比",
        "dynamic_control": "宁凡眼中的光芒破碎",
        "dialogue": "宁凡(内心独白): \"七年...我的七年...\""
    },
    {
        "shot_number": 17,
        "title": "举起手机",
        "subject": "宁凡、手机礼盒",
        "shot_type": "中景 - 宁凡颤抖着举起手中的手机礼盒",
        "atmosphere": "冷色、愤怒",
        "environment": "保时捷车窗前",
        "camera_movement": "第1个宁凡全身颤抖，切镜第2个手部握紧礼盒",
        "angle": "第1个侧面中景，第2个手部特写",
        "special_technique": "切镜、慢动作",
        "composition": "中景切特写",
        "style": "电影质感",
        "dynamic_control": "宁凡手臂颤抖着举起",
        "dialogue": "无"
    },
    {
        "shot_number": 18,
        "title": "砸向车窗",
        "subject": "手机礼盒、车窗",
        "shot_type": "特写 - 手机礼盒狠狠砸向车窗的瞬间",
        "atmosphere": "冷色、爆发",
        "environment": "车窗",
        "camera_movement": "高速摄影（慢动作）",
        "angle": "侧面特写",
        "special_technique": "慢动作、玻璃碎裂特效",
        "composition": "特写",
        "style": "电影质感、高速摄影",
        "dynamic_control": "手机礼盒撞击车窗，玻璃开始碎裂",
        "dialogue": "无"
    },
    {
        "shot_number": 19,
        "title": "玻璃碎裂",
        "subject": "碎裂的车窗、玻璃碎片",
        "shot_type": "特写 - 车窗玻璃碎裂，碎片飞溅",
        "atmosphere": "冷色、震撼",
        "environment": "车窗",
        "camera_movement": "高速摄影（慢动作），多角度切镜",
        "angle": "第1个正面特写玻璃碎裂，第2个侧面碎片飞溅，第3个车内视角",
        "special_technique": "高速摄影、多角度切镜",
        "composition": "特写切特写切特写",
        "style": "电影质感、慢动作",
        "dynamic_control": "玻璃碎裂的声音与七年付出碎裂的声音重叠",
        "dialogue": "(音效): \"哐当！\""
    },
    {
        "shot_number": 20,
        "title": "碎片落地",
        "subject": "玻璃碎片、地面",
        "shot_type": "特写 - 玻璃碎片缓缓落在地面",
        "atmosphere": "冷色、寂静",
        "environment": "停车场地面",
        "camera_movement": "慢动作下降跟拍",
        "angle": "低角度特写",
        "special_technique": "慢动作、声音设计（回声）",
        "composition": "特写",
        "style": "电影质感",
        "dynamic_control": "碎片在空中旋转落下",
        "dialogue": "无"
    },
    {
        "shot_number": 21,
        "title": "车内惊恐",
        "subject": "杨琪琪、陈伟",
        "shot_type": "中景 - 车内两人惊叫着分开",
        "atmosphere": "冷色、混乱",
        "environment": "保时捷车内",
        "camera_movement": "第1个两人惊恐分开，切镜第2个陈伟手忙脚乱提裤子",
        "angle": "第1个车内全景，第2个陈伟中景",
        "special_technique": "切镜",
        "composition": "中景切中景",
        "style": "电影质感",
        "dynamic_control": "两人慌乱整理衣物",
        "dialogue": "杨琪琪(惊叫): \"啊！\"\n陈伟: \"什么人？！\""
    },
    {
        "shot_number": 22,
        "title": "宁凡站在碎窗前",
        "subject": "宁凡",
        "shot_type": "中景 - 宁凡站在碎裂的车窗前，手还保持着砸窗的姿势",
        "atmosphere": "冷色、悲愤",
        "environment": "保时捷车旁",
        "camera_movement": "固定",
        "angle": "正面中景",
        "special_technique": "逆光剪影效果",
        "composition": "中景",
        "style": "电影质感、低饱和度",
        "dynamic_control": "宁凡身体微微颤抖，眼神中是绝望和愤怒",
        "dialogue": "无"
    },
    {
        "shot_number": 23,
        "title": "四目相对",
        "subject": "宁凡、杨琪琪",
        "shot_type": "特写对切 - 宁凡和杨琪琪四目相对",
        "atmosphere": "冷色、凝固",
        "environment": "车窗两侧",
        "camera_movement": "第1个宁凡特写，切镜第2个杨琪琪特写，切镜第3个两人对视",
        "angle": "正面特写对切",
        "special_technique": "快速切镜、表情对比",
        "composition": "特写切特写切双人镜",
        "style": "电影质感",
        "dynamic_control": "宁凡眼中是破碎，杨琪琪眼中从惊恐变为冷漠",
        "dialogue": "宁凡(声音沙哑): \"七年...我供你上学七年...你就是这么回报我的？\""
    },
    {
        "shot_number": 24,
        "title": "杨琪琪的冷漠",
        "subject": "杨琪琪",
        "shot_type": "近景 - 杨琪琪整理衣服，表情从慌乱变得冷漠",
        "atmosphere": "冷色、势利",
        "environment": "保时捷车内",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "表情递进",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "杨琪琪冷漠地整理衣服，眼神闪躲",
        "dialogue": "杨琪琪(冷漠): \"既然你已经看到了，我也没什么好说的。\""
    },
    {
        "shot_number": 25,
        "title": "陈伟嘲笑",
        "subject": "陈伟",
        "shot_type": "中景 - 陈伟大笑着走出车门，居高临下看着宁凡",
        "atmosphere": "冷色、嚣张",
        "environment": "保时捷车门旁",
        "camera_movement": "第1个陈伟下车，切镜第2个低角度仰拍陈伟",
        "angle": "第1个侧面中景，第2个低角度仰拍",
        "special_technique": "低角度强调压迫感",
        "composition": "中景切仰拍中景",
        "style": "电影质感",
        "dynamic_control": "陈伟整理西装，不屑地笑",
        "dialogue": "陈伟(大笑): \"我当是谁，原来是杨琪琪那个送快递的老公。\""
    },
    {
        "shot_number": 26,
        "title": "阶级对比",
        "subject": "陈伟、宁凡",
        "shot_type": "双人镜 - 陈伟居高临下，宁凡愤怒对视",
        "atmosphere": "冷色、对峙",
        "environment": "保时捷旁",
        "camera_movement": "缓慢环绕",
        "angle": "双人对峙构图",
        "special_technique": "构图强调阶级差异",
        "composition": "双人中景",
        "style": "电影质感",
        "dynamic_control": "两人对峙，气氛紧张",
        "dialogue": "陈伟: \"兄弟，别怪我。你老婆是自己贴上来的。你一个废物，看见又怎样？\""
    },
    {
        "shot_number": 27,
        "title": "杨琪琪补刀",
        "subject": "杨琪琪",
        "shot_type": "近景 - 杨琪琪冷笑着看向宁凡",
        "atmosphere": "冷色、讽刺",
        "environment": "车内",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "聚焦表情",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "杨琪琪冷笑，眼中是鄙夷",
        "dialogue": "杨琪琪(冷笑): \"回报？宁凡，你看看你自己。一个送快递的，能给我什么？陈伟一个月的零花钱，够你挣一辈子。\""
    },
    {
        "shot_number": 28,
        "title": "宁凡的反击",
        "subject": "宁凡、手机",
        "shot_type": "中景 - 宁凡弯腰捡起地上砸烂的手机",
        "atmosphere": "冷色、愤怒",
        "environment": "停车场地面",
        "camera_movement": "第1个宁凡弯腰，切镜第2个手部捡起手机",
        "angle": "第1个侧面中景，第2个手部特写",
        "special_technique": "切镜",
        "composition": "中景切特写",
        "style": "电影质感",
        "dynamic_control": "宁凡动作缓慢而坚定",
        "dialogue": "无"
    },
    {
        "shot_number": 29,
        "title": "手机砸向陈伟",
        "subject": "宁凡、陈伟、手机",
        "shot_type": "中景 - 宁凡猛地抡起手机砸向陈伟的头",
        "atmosphere": "冷色、爆发",
        "environment": "停车场",
        "camera_movement": "高速摄影，第1个宁凡挥臂，切镜第2个手机撞击陈伟额头",
        "angle": "第1个侧面中景，第2个特写撞击瞬间",
        "special_technique": "慢动作、撞击特写",
        "composition": "中景切特写",
        "style": "电影质感、高速摄影",
        "dynamic_control": "宁凡爆发力量，手机砸向陈伟",
        "dialogue": "(音效): \"砰！\""
    },
    {
        "shot_number": 30,
        "title": "陈伟捂头",
        "subject": "陈伟",
        "shot_type": "近景 - 陈伟捂着流血的额头，难以置信",
        "atmosphere": "冷色、震惊",
        "environment": "停车场",
        "camera_movement": "固定",
        "angle": "正面近景",
        "special_technique": "血液效果",
        "composition": "近景",
        "style": "电影质感",
        "dynamic_control": "陈伟捂着额头，血从指缝流下",
        "dialogue": "陈伟(瞪大眼睛): \"你...你敢打我？！你知道我爸是谁吗？！\""
    },
    {
        "shot_number": 31,
        "title": "废物的反击",
        "subject": "宁凡",
        "shot_type": "特写 - 宁凡坚定的眼神",
        "atmosphere": "冷色、坚定",
        "environment": "停车场",
        "camera_movement": "缓慢推进",
        "angle": "正面特写",
        "special_technique": "缓推强调决心",
        "composition": "特写渐变大特写",
        "style": "电影质感",
        "dynamic_control": "宁凡眼中燃起怒火",
        "dialogue": "宁凡(一字一顿): \"我是废物。但废物也有脾气。\""
    },
    {
        "shot_number": 32,
        "title": "第一部分结束画面",
        "subject": "宁凡、陈伟对峙",
        "shot_type": "远景 - 停车场中两人对峙的剪影",
        "atmosphere": "冷色、紧张",
        "environment": "昏暗的停车场",
        "camera_movement": "缓慢拉远",
        "angle": "高角度俯拍",
        "special_technique": "剪影效果",
        "composition": "远景",
        "style": "电影质感、高对比度",
        "dynamic_control": "两人对峙，陈伟在打电话叫人",
        "dialogue": "陈伟(疯狂按手机): \"给我打！往死里打！\""
    }
]


def create_styles(font_name):
    """Create PDF styles"""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=24,
        leading=30,
        alignment=1,
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a2e')
    ))

    styles.add(ParagraphStyle(
        name='ChineseSubtitle',
        fontName=font_name,
        fontSize=14,
        leading=18,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor('#666666')
    ))

    styles.add(ParagraphStyle(
        name='ShotHeader',
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#d4380d'),
        borderColor=colors.HexColor('#d4380d'),
        borderWidth=1,
        borderPadding=5,
        backColor=colors.HexColor('#fff2e8')
    ))

    styles.add(ParagraphStyle(
        name='FieldLabel',
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#333333'),
        fontWeight='bold'
    ))

    styles.add(ParagraphStyle(
        name='FieldValue',
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
        leftIndent=10
    ))

    styles.add(ParagraphStyle(
        name='Dialogue',
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#8B0000'),
        leftIndent=10,
        backColor=colors.HexColor('#fff5f5'),
        borderPadding=5
    ))

    return styles


def create_shot_table(shot_data, styles, font_name):
    """Create a table for a single shot"""
    fields = [
        ("主体", shot_data["subject"]),
        ("景别", shot_data["shot_type"]),
        ("氛围", shot_data["atmosphere"]),
        ("环境", shot_data["environment"]),
        ("运镜", shot_data["camera_movement"]),
        ("视角", shot_data["angle"]),
        ("特殊拍摄手法", shot_data["special_technique"]),
        ("构图", shot_data["composition"]),
        ("风格统一", shot_data["style"]),
        ("动态控制", shot_data["dynamic_control"]),
        ("台词", shot_data["dialogue"]),
    ]

    table_data = []
    for label, value in fields:
        label_para = Paragraph(f"<b>{label}:</b>", styles['FieldLabel'])
        if label == "台词" and value != "无":
            value_para = Paragraph(value.replace("\n", "<br/>"), styles['Dialogue'])
        else:
            value_para = Paragraph(value, styles['FieldValue'])
        table_data.append([label_para, value_para])

    table = Table(table_data, colWidths=[80, 400])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 5),
        ('RIGHTPADDING', (1, 0), (1, -1), 5),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fff7e6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ffd591')),
    ]))

    return table


def generate_pdf(output_filename=None):
    """Generate the storyboard PDF"""
    font_name = register_chinese_font()

    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"storyboard_ep1_part1_{timestamp}.pdf"

    output_path = OUTPUT_DIR / output_filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = create_styles(font_name)
    story = []

    # Title page
    story.append(Spacer(1, 50*mm))
    story.append(Paragraph("分镜脚本", styles['ChineseTitle']))
    story.append(Paragraph("离婚后躺女总裁床上，前妻急了？", styles['ChineseSubtitle']))
    story.append(Paragraph("第一集（上）：开场 至 砸车窗", styles['ChineseSubtitle']))
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['ChineseSubtitle']))
    story.append(Paragraph(f"共 {len(STORYBOARD_DATA)} 个分镜", styles['ChineseSubtitle']))
    story.append(PageBreak())

    # Shot pages
    for i, shot in enumerate(STORYBOARD_DATA):
        header_text = f"=== 分镜 {shot['shot_number']} === {shot['title']}"
        story.append(Paragraph(header_text, styles['ShotHeader']))
        story.append(Spacer(1, 5*mm))

        table = create_shot_table(shot, styles, font_name)
        story.append(table)

        if i < len(STORYBOARD_DATA) - 1:
            if (i + 1) % 3 == 0:
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 10*mm))

    doc.build(story)
    print(f"PDF generated: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    output_path = generate_pdf()
    print(f"\nStoryboard PDF saved to: {output_path}")
