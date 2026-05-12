from .models import CommandesProduits

def cart_item_count(request):
    if request.user.is_authenticated:
        # On filtre les lignes de commande liées au client dont l'utilisateur est le user connecté
        count = CommandesProduits.objects.filter(
            commande__client__utilisateur=request.user,
            commande__statut='panier'   # uniquement la commande en cours
        ).count()
    else:
        count = 0
    return {'cart_item_count': count}
