from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import yt_dlp
import cohere
import os
import json
import assemblyai as aai
from .models import BlogPost


@login_required
def index(request):
    return render(request, 'index.html')


@csrf_exempt
@login_required
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        title = yt_title(yt_link)
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript"}, status=500)
        print(transcription)
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)

        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        print(type(blog_content))
        print(blog_content)

        return JsonResponse({'content': f"{blog_content[:500]}..."})
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



def yt_title(link):
    ydl_opts = {
        'cookiefile': 'static/cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        return info.get('title', 'No Title Found')


def download_audio(link):
    output_dir = settings.MEDIA_ROOT
    output_template = os.path.join(output_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'cookiefile': 'static/cookies.txt',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + '.mp3'
        return mp3_filename


def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    if os.path.exists(audio_file):
        os.remove(audio_file)
    print("You came here \n\n\n\n")
    print(transcript.text)
    return transcript.text

def get_blog_generation_prompt(transcription: str) -> str:
    """
    Takes a transcript and embeds it into a prompt designed to generate a
    well-structured blog post as clean, unformatted plain text.
    """
    
    # Using a triple-quoted f-string for a clean, multi-line prompt.
    prompt = f"""
Act as an expert blog writer and content strategist, specializing in transforming spoken content into compelling, high-quality articles for platforms like Medium. Your task is to take the following transcript and write a complete, original, and seamless blog post as clean, well-structured plain text.

CRITICAL INSTRUCTIONS:
- The entire output MUST be a single, continuous block of plain text.
- The output must be a fully-formed article, ready to be published.
- Do NOT include any placeholders, bracketed instructions, or fields to be filled in.
- Do NOT use any HTML or Markdown formatting (e.g., no `#` for titles, no `*` for lists).
- Synthesize the core ideas from the transcript into a new, well-structured written piece. Do not simply rephrase the transcript.

CONTENT STRUCTURE REQUIREMENTS (Use Plain Text):

1.  Title: Start with a single, engaging title on its own line.
2.  Introduction: Follow with a powerful and inspiring introduction that hooks the reader. Use a blank line to separate it from the title.
3.  Body:
    -   Structure the main content with clear paragraphs, separated by blank lines.
    -   Use clear subheadings on their own lines to organize the major sections of the article.
    -   For lists of items, simply place each item on a new line.
4.  Key Takeaways Section (If Applicable):
    -   Create a distinct section with a subheading like "Key Takeaways" on its own line. List the key points, with each point on a new line.
5.  Conclusion: End with a strong concluding paragraph that summarizes the main message and offers a final, memorable thought or a clear call to action.
Follow the requirements and instructions stickly
Here is the transcript:
\"\"\"
{transcription}
\"\"\"
"""
    return prompt




def generate_blog_from_transcription(transcription: str) -> str:
    api_key = settings.COHERE_API_KEY

    co = cohere.ClientV2(api_key=api_key)

    prompt = get_blog_generation_prompt(transcription)

    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=1000
    )
    print(response.message.content[0].text)
    return response.message.content[0].text.strip()




# --------------------------- Blog List and Details ---------------------------

@login_required
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    # print(blog_articles)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

@login_required
def blog_details(request, pk):
    try:
        blog_article_detail = BlogPost.objects.filter(id=pk, user=request.user).first()
        # print("I am in blog")
        # print(type(blog_article_detail))
        # print(blog_article_detail)
        return render(request, 'blog-details.html', {'blog_article_details': blog_article_detail})
    except BlogPost.DoesNotExist:
        return redirect('/')

# --------------------------- Authentication ---------------------------

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'login.html', {'error_message': "Invalid username or password"})
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        repeat_password = request.POST.get('repeatPassword')

        if password != repeat_password:
            return render(request, 'signup.html', {'error_message': 'Passwords do not match'})

        try:
            user = User.objects.create_user(username, email, password)
            login(request, user)
            return redirect('/')
        except:
            return render(request, 'signup.html', {'error_message': 'Error creating account'})

    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

def transcribe_uploaded_audio(file_path):
    aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

    transcriber = aai.Transcriber()

    transcript = transcriber.transcribe(file_path)

    # WAIT until transcription finishes
    transcript.wait_for_completion()

    if transcript.status == aai.TranscriptStatus.completed:
        return transcript.text
    else:
        raise Exception(f"Transcription failed: {transcript.status}")

@csrf_exempt
@login_required
def generate_blog_from_audio(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": "No audio uploaded"}, status=400)

    temp_path = None

    try:
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            for chunk in audio_file.chunks():
                temp_audio.write(chunk)
            temp_path = temp_audio.name

        transcription = transcribe_uploaded_audio(temp_path)

        blog_content = generate_blog_from_transcription(transcription)

        BlogPost.objects.create(
            user=request.user,
            youtube_title="Audio Recording",
            youtube_link="Recorded Audio",
            generated_content=blog_content,
        )

        return JsonResponse({"content": blog_content[:500] + "..."})

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
