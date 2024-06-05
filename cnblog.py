# export CNBLOG_TOKEN=xxxxxxx
# python cnblog.py posts/cloud/kubernetes-certs-renew.md
import os
import argparse
import toml
import xmlrpc.client
from urllib.parse import quote

def parse_front_matter(content):
    """解析文件开头的 front matter（支持 TOML 格式）"""
    if content.startswith('+++'):
        end_index = content.find('+++', 3)
        if end_index != -1:
            front_matter_content = content[3:end_index].strip()
            front_matter = toml.loads(front_matter_content)
            # 去掉 front matter 后的内容
            content = content[end_index + 3:].strip()
            return front_matter, content
    return {}, content

def process_markdown(input_file, original_url):
    try:
        # 读取Markdown文件内容
        with open(input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 解析 front matter
        front_matter, content = parse_front_matter(content)
        
        # 获取 title
        title = front_matter.get('title', 'Untitled')
        tags = front_matter.get('tags', [])
        
        # 找到 `<!--more-->` 的位置
        more_index = content.find('<!--more-->')
        
        # 如果找到了 `<!--more-->`，去掉之前的内容
        if more_index != -1:
            content = content[more_index + len('<!--more-->'):].strip()
        
        # 在文章最前面插入原文链接
        content = f"原文链接：{original_url}\n\n" + content
        
        return title, content, tags
    
    except FileNotFoundError:
        print(f'文件 {input_file} 不存在')
        return None, None
    except Exception as e:
        print(f'处理文件时发生错误: {e}')
        return None, None

def publish_to_cnblogs(username, content, title, tags):
    # 博客园 MetaWeblog API URL
    API_URL = 'https://rpc.cnblogs.com/metaweblog/'+username

    # 你的博客园用户名和密码
    USERNAME = username
    PASSWORD = os.getenv('CNBLOG_TOKEN')

    if not USERNAME or not PASSWORD:
        print('请确保环境变量 CNBLOG_TOKEN 已设置')
        return

    # 构建文章数据
    post = {
        'title': title,
        'description': content,
        'categories': ['[Markdown]'],
        'mt_keywords': tags,  # 文章标签
        'post_type': 'markdown'  # 指定文章类型为markdown
    }

    # 发布文章
    client = xmlrpc.client.ServerProxy(API_URL)
    try:
        post_id = client.metaWeblog.newPost('', USERNAME, PASSWORD, post, True)
        print(f'文章发布成功，文章ID: {post_id}')
    except Exception as e:
        print(f'发布文章失败: {e}')

if __name__ == '__main__':

    username = 'maoqide'
    parser = argparse.ArgumentParser(description='发布Markdown文章到博客园')
    parser.add_argument('input_file', help='输入的Markdown文件路径')

    args = parser.parse_args()

    # 生成原文链接，去掉文件的 .md 后缀并进行 URL 编码
    original_url = quote(os.path.splitext(args.input_file)[0])
    title, content, tags = process_markdown('content/'+args.input_file, 'https://maoqide.live/'+original_url)
    if content:
        publish_to_cnblogs(username, content, title, tags)