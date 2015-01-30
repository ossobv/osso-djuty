from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.db.models import Q

from osso.cms.members.models import Group, Member
from osso.cms.members.forms import GroupForm, MemberAddForm, MemberForm

@login_required
def group(request):
    groups = request.user.group_set.all()
    context = RequestContext(request, {'groups': groups,})
    return render_to_response('members/group_overview.html', context)

@login_required
def group_add(request):
    if request.method == 'POST':
        form = GroupForm(data=request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.user = request.user
            group.save()
            return HttpResponseRedirect(reverse('groups'))
    else:
        form = GroupForm()

    context = RequestContext(request, {
           'form': form
        }
    )
    return render_to_response('members/group_add.html', context)

@login_required
def group_edit(request, group_id):
    group = get_object_or_404(Group, pk=group_id, user=request.user)
    if request.method == 'POST':
        form = GroupForm(data=request.POST, instance=group)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('groups'))
    else:
        form = GroupForm(instance=group)
    context = RequestContext(request, {
           'group': group,
           'form': form
        }
    )
    return render_to_response('members/group_edit.html', context)

@login_required
def group_delete(request, group_id):
    group = get_object_or_404(Group, pk=group_id, user=request.user)
    if request.method == 'POST':
        if 'yes' in request.POST:
            group.delete()
        return HttpResponseRedirect(reverse('groups'))
    context = RequestContext(request, {'group': group})
    return render_to_response('members/group_delete.html', context)

@login_required
def group_add_member(request, group_id):
    group = get_object_or_404(Group, pk=group_id, user=request.user)
    other_members = Member.objects.exclude(group=group).filter(Q(user=request.user)|Q(group__in=request.user.group_set.all())).distinct()

    if request.method == 'POST':
        form = MemberAddForm(data=request.POST, members=other_members)
        if form.is_valid():
            member = form.get_member()
            member.user = request.user
            member.group.add(group)
            member.save()
            return HttpResponseRedirect(reverse('group_edit', args=[group.id]))
    else:
        form = MemberAddForm(members=other_members)

    context =  RequestContext(request, {
            'group': group,
            'form': form,
        }
    )
    return render_to_response('members/group_add_member.html', context)

@login_required
def group_remove_member(request, group_id, member_id):
    group = get_object_or_404(Group, pk=group_id, user=request.user)
    member = get_object_or_404(Member, pk=member_id, group=group)

    if request.method == 'POST' and 'yes' in request.POST:
        member.group.remove(group)
        return HttpResponseRedirect(reverse('group_edit', args=[group.id]))

    context = RequestContext(request, {'group': group, 'member': member})
    return render_to_response('members/group_remove_member.html', context)

@login_required
def members(request):
    members = Member.objects.filter(Q(user=request.user)|Q(group__in=request.user.group_set.all())).distinct()
    context = RequestContext(request, {
            'members': members,
        }
    )
    return render_to_response('members/members_overview.html', context)

@login_required
def member_add(request):
    if request.method == 'POST':
        form = MemberForm(data=request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.user = request.user
            member.save()
            return HttpResponseRedirect(reverse('members'))
    else:
        form = MemberForm()

    context =  RequestContext(request, {
            'form': form
        }
    )
    return render_to_response('members/member_add.html', context)

@login_required
def member_edit(request, member_id):
    member = get_object_or_404(
       Member.objects.filter(Q(user=request.user)|Q(group__in=request.user.group_set.all())).distinct(),
       pk=member_id
    )

    if request.method == 'POST':
        form = MemberForm(data=request.POST, instance=member)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('members'))
    else:
        form = MemberForm(instance=member)

    context =  RequestContext(request, {
            'member': member,
            'form': form
        }
    )
    return render_to_response('members/member_edit.html', context)

@login_required
def member_delete(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        if 'yes' in request.POST:
            member.delete()
        return HttpResponseRedirect(reverse('members'))
    context = RequestContext(request, {'member': member})
    return render_to_response('members/member_delete.html', context)
