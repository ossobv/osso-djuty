from cms.models.pagemodel import Page

def remove_menu_item(navigation_tree, request):
    if request.user.is_authenticated():
        for node in navigation_tree:
            if isinstance(node, Page) and node.get_application_urls() == 'osso.cms.registration.urls':
                navigation_tree.remove(node)
    return navigation_tree
