from random import choices
from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Lesson, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic,View
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(View):
    #model = Course
    #template_name = 'onlinecourse/course_detail_bootstrap.html'
    def get(self,request,pk):
        lesson_data = Lesson.objects.filter(course_id = pk).select_related('course')
        data_id = []
        lesson = []
        for i in lesson_data:
            data = {}
            data['course_name'] = i.course.name
            data['order'] = i.order
            data['title'] = i.title
            data['content'] = i.content
            data['lesson_id'] = i.id
            data_id.append(i.id)#collects list of lesson id to get questions
            lesson.append(data)
        Questions_data = Question.objects.filter(lesson__in = data_id).select_related('lesson')
        data_id = []
        Questions = []
        for i in Questions_data:
            data = {}
            data['question_id'] = i.id
            data['question_text'] = i.question
            data['mark'] = i.mark
            data['visibility_status'] = i.visibility_status
            data['lesson_id'] = i.lesson.id
            data_id.append(i.id)#collects list of questions to obtain the choices related to this questions
            Questions.append(data)
        Choices_data = Choice.objects.filter(question__in = data_id).select_related('question')
        Choices = []
        for i in Choices_data:
            data = {}
            data['id'] = i.id
            data['choice_text'] = i.content
            data['visibility_status'] = i.visibility_status#Visibility status is used to hide/unhide options from users
            data['question_id'] = i.question.id
            Choices.append(data)
        content = {'lessons':lesson,'questions':Questions,'choices':Choices}
        return render(request,'onlinecourse/course_detail_bootstrap.html',content)


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    enrollment = Enrollment.objects.get(user = request.user.id, course = course_id)
    sub_id = Submission( enrollment = enrollment )
    sub_id.save()
    post_data = request.POST
    for choices in post_data:
        if choices == 'csrfmiddlewaretoken':
            pass
        else:
            choice_id = Choice.objects.get(id = post_data[choices])
            sub_id.choices.add(choice_id)
    return redirect('/onlinecourse/'+str(course_id)+'/submission/'+str(sub_id.id)+'/results/')

# <HINT> A example method to collect the selected choices from the exam form from the request object
#def extract_answers(request):
#    submitted_anwsers = []
#    for key in request.POST:
#        if key.startswith('choice'):
#            value = request.POST[key]
#            choice_id = int(value)
#            submitted_anwsers.append(choice_id)
#    return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    #print(course_id, submission_id)
    submitted_answers = Submission.objects.get(id = submission_id).choices.all()
    total_score,achived_score = 0,0
    user_choices,question_list,choice_list = [],[],[]
    lesson_id = 0
    question_id = []
    for i in submitted_answers:
        user_choices.append(i.id)
        if i.correct_choice == True:
            achived_score = achived_score + i.question.mark
        total_score = total_score +i.question.mark
        lesson_id = i.question.lesson
    questions = Question.objects.filter(lesson = lesson_id)
    for i in questions:
        data = {}
        data['question_id'] = i.id
        data['question_text'] = i.question
        data['mark'] = i.mark
        data['visibility_status'] = i.visibility_status
        question_id.append(i.id)
        question_list.append(data)
    print(question_id)
    choices = Choice.objects.filter(question__in = question_id)
    for i in choices:
        data = {}
        data['id'] = i.id
        data['choice_text'] = i.content
        data['visibility_status'] = i.visibility_status#Visibility status is used to hide/unhide options from users
        data['correct_choice'] = i.correct_choice
        data['question_id'] = i.question.id
        choice_list.append(data)  
    content = { 'course':course_id,'selected_id':user_choices,'achived_score':achived_score,'total_score':total_score,"grade":(achived_score/total_score)*100,'questions':question_list,'choices':choice_list}
    #print(content)
    return render(request, 'onlinecourse/exam_result_bootstrap.html',content)
    


