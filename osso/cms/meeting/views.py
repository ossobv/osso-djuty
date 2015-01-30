import random

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy as _
from django.forms.util import ErrorList

from osso.cms.meeting.forms import InviteForm, InviteGroupForm, MeetingInvitationPeopleForm
from osso.cms.meeting.models import Meeting, Invite
from osso.cms.meeting.utils import sender_notification
from osso.cms.members.models import Group, Member

def invite(request):
    user = request.user

    if user.is_authenticated():
        meeting_form = InviteGroupForm
        initial = {'name': user.first_name}
        groups = user.group_set.all()
    else:
        meeting_form = InviteForm
        initial = {}
        groups = None

    if request.method == 'POST':
        form = meeting_form(data=request.POST, initial=initial, groups=groups)
        formset = MeetingInvitationPeopleForm(data=request.POST, queryset=Member.objects.none())

        if form.is_valid() and formset.is_valid():
            if not formset.save(commit=False) and not form.cleaned_data.get('group', None):
                formset.non_form_errors = ErrorList([_('There must be at least 1 person to be invited.'),])
            else:
                if user.is_authenticated() and form.cleaned_data['group'] is None and form.cleaned_data['group_text'] not in (None, ''):
                    group = Group.objects.get_or_create(name=form.cleaned_data['group_text'], user=user)
                    form.cleaned_data['group'] = group[0]
                else:
                    group = (None, False)

                meeting = form.save(commit=False)
                if user.is_authenticated():
                    meeting.user = user
                    if user.first_name in (None, '') or user.first_name != meeting.name:
                        user.first_name = meeting.name
                        user.save()
                meeting.save()

                members = formset.save_new_objects()

                if group[1]:
                    for m in members:
                        m.group.add(group[0])
                        m.save()
                elif meeting.group:
                    members = meeting.group.members.all()

                for member in members:
                    token = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for i in range(16)])
                    Invite.objects.create(meeting=meeting, member=member, token=token)

                context = RequestContext(request)
                return render_to_response('meeting/thnx.html', context)
    else:
        form = meeting_form(initial=initial, groups=groups)
        formset = MeetingInvitationPeopleForm(queryset=Member.objects.none())

    context = RequestContext(request, {'form': form, 'formset': formset,})
    return render_to_response('meeting/invite.html', context)

def meeting_invite_accept(request, invite_id, token):
    invite = get_object_or_404(Invite, id=invite_id, token=token)
    invite.accept = True
    invite.save()
    #Send mail to meeting sender that the member has accepted the meeting
    sender_notification(invite, _('accepted'))
    context = RequestContext(request, {'invite': invite, 'notification_string': _('accepted')})
    return render_to_response('meeting/meeting_invitation.html', context)


def meeting_invite_reject(request, invite_id, token):
    invite = get_object_or_404(Invite, id=invite_id, token=token)
    invite.accept = False
    invite.save()
    #Send mail to meeting sender that the member has not accepted the meeting
    sender_notification(invite, _('not accepted'))
    context = RequestContext(request, {'invite': invite, 'notification_string': _('not accepted')})
    return render_to_response('meeting/meeting_invitation.html', context)

@login_required
def meeting(request):
    meetings = request.user.meeting_set.all()
    context = RequestContext(request, {'meetings': meetings,})
    return render_to_response('meeting/meeting_overview.html', context)

@login_required
def meeting_detail(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, user=request.user)
    context = RequestContext(request, {'meeting': meeting,})
    return render_to_response('meeting/meeting_detail.html', context)
