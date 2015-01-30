from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from cms.utils.navigation import NavigationNode

def get_nodes(request):
    nodes = []
    if request.user.is_authenticated():
        nodes.append(NavigationNode(_('Groups'), reverse('groups')))
        nodes.append(NavigationNode(_('Members'), reverse('members')))
        nodes.append(NavigationNode(_('Meeting invitations'), reverse('meeting')))
    return nodes
