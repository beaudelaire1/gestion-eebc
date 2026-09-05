"""
Vues pour la gestion des familles.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from apps.core.permissions import role_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from apps.core.models import Family, Neighborhood, Site
from .models import Member


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def family_list(request):
    """Liste des familles."""
    families = Family.objects.select_related('site', 'neighborhood', 'neighborhood__city').order_by('name')
    
    # Filtres
    site_id = request.GET.get('site')
    neighborhood_id = request.GET.get('neighborhood')
    search = request.GET.get('search')
    
    if site_id:
        families = families.filter(site_id=site_id)
    if neighborhood_id:
        families = families.filter(neighborhood_id=neighborhood_id)
    if search:
        # Une famille se cherche aussi par le nom d'une des personnes du foyer :
        # le nom du foyer n'est pas toujours celui qu'on a en tête.
        families = families.filter(
            Q(name__icontains=search)
            | Q(members__first_name__icontains=search)
            | Q(members__last_name__icontains=search)
        ).distinct()

    context = {
        'families': families,
        'sites': Site.objects.filter(is_active=True),
        'neighborhoods': Neighborhood.objects.filter(is_active=True).select_related('city'),
        'total_count': families.count(),
    }

    # Le formulaire de recherche ne remplace que la liste : renvoyer la page
    # entière dans #family-content empilerait la page dans elle-même.
    if getattr(request, 'htmx', False):
        return render(request, 'members/partials/family_list_content.html', context)
    return render(request, 'members/family_list.html', context)


def _build_household_tree(members):
    """Range les membres d'un foyer par génération, pour l'arbre.

    Le modèle FamilyRelationship décrit des liens de parenté précis, mais
    aucune relation n'a jamais été saisie : dessiner à partir de là donnerait
    un arbre vide pour tout le monde. Member.family_role, lui, est renseigné.
    L'arbre représente donc le foyer — parents, couple, enfants — c'est-à-dire
    ce que les données disent réellement, et non une généalogie supposée.
    """
    buckets = {'PARENT': [], 'HEAD': [], 'SPOUSE': [], 'CHILD': [], 'OTHER': []}
    for member in members:
        buckets.get(member.family_role, buckets['OTHER']).append(member)

    couple = buckets['HEAD'] + buckets['SPOUSE']

    # Sans chef de famille désigné, un foyer d'adultes n'afficherait que des
    # enfants suspendus dans le vide : le premier membre sert d'ancrage.
    if not couple and not buckets['PARENT'] and buckets['OTHER']:
        couple = [buckets['OTHER'].pop(0)]

    return {
        'parents': buckets['PARENT'],
        'couple': couple,
        'children': buckets['CHILD'],
        'others': buckets['OTHER'],
        'has_any': any([buckets['PARENT'], couple, buckets['CHILD'], buckets['OTHER']]),
    }


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def family_detail(request, pk):
    """Détail d'une famille."""
    family = get_object_or_404(
        Family.objects.select_related('site', 'neighborhood', 'neighborhood__city'),
        pk=pk
    )

    members = family.members.select_related(
        'young_profile', 'bibleclub_profile',
    ).order_by('-family_role', 'last_name', 'first_name')

    # Listes compactes pour la sidebar (ordre logique : enfants -> jeunes)
    bibleclub_children = list(
        family.bibleclub_children.select_related('bible_class').order_by('last_name', 'first_name')
    ) if hasattr(family, 'bibleclub_children') else []
    young_members = list(
        family.young_members.select_related('group').order_by('last_name', 'first_name')
    ) if hasattr(family, 'young_members') else []

    context = {
        'family': family,
        'members': members,
        'tree': _build_household_tree(members),
        'bibleclub_children': bibleclub_children,
        'young_members': young_members,
    }

    return render(request, 'members/family_detail.html', context)


@login_required
@role_required('admin', 'secretariat')
def family_delete(request, pk):
    """Supprimer une famille, sans emporter ses membres.

    On pouvait créer et modifier une famille, jamais en supprimer une : la
    route n'existait pas. Un foyer se dissout pourtant — déménagement,
    séparation, saisie en double — et la fiche restait indéfiniment.

    Le lien member.family est SET_NULL : supprimer le foyer détache ses
    membres, il ne les efface pas. La page de confirmation le dit, parce que
    l'inverse est ce qu'on redoute en cliquant.
    """
    family = get_object_or_404(Family, pk=pk)
    members = family.members.order_by('last_name', 'first_name')

    if request.method == 'POST':
        name = family.name
        detached = members.count()
        family.delete()
        if detached:
            messages.success(
                request,
                f"Famille '{name}' supprimée. "
                f"{detached} membre(s) conservé(s), désormais sans famille.",
            )
        else:
            messages.success(request, f"Famille '{name}' supprimée.")
        return redirect('members:family_list')

    return render(request, 'members/family_delete_confirm.html', {
        'family': family,
        'members': members,
    })


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def member_api_data(request, pk):
    """Retourne les données d'un membre en JSON pour l'auto-remplissage du formulaire famille.
    
    Fallback : si le membre n'a pas d'adresse/téléphone/email, on retourne
    ceux de sa famille existante.
    """
    member = get_object_or_404(Member.objects.select_related('family', 'site'), pk=pk)
    family = member.family
    return JsonResponse({
        'last_name': member.last_name,
        'first_name': member.first_name,
        'email': member.email or (family.email if family else ''),
        'phone': member.phone or (family.phone if family else ''),
        'address': member.address or (family.address if family else ''),
        'city': member.city or (family.city if family else ''),
        'postal_code': member.postal_code or (family.postal_code if family else ''),
        'site_id': member.site_id or (family.site_id if family else '') or '',
    })


@login_required
@role_required('admin', 'secretariat')
def family_create(request):
    """Créer une nouvelle famille."""
    if request.method == 'POST':
        name = request.POST.get('name')
        site_id = request.POST.get('site')
        neighborhood_id = request.POST.get('neighborhood') or None
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        postal_code = request.POST.get('postal_code', '')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        
        family = Family.objects.create(
            name=name,
            site_id=site_id if site_id else None,
            neighborhood_id=neighborhood_id,
            address=address,
            city=city,
            postal_code=postal_code,
            phone=phone,
            email=email,
        )
        
        messages.success(request, f"Famille '{name}' créée avec succès.")
        return redirect('members:family_detail', pk=family.pk)
    
    # Membres disponibles avec toutes les infos pour UX enrichie (photo, site, téléphone)
    available_members = Member.objects.filter(
        status='actif'
    ).select_related(
        'site'
    ).only(
        'id', 'first_name', 'last_name', 'photo', 'phone', 'site__name'
    ).order_by('last_name', 'first_name')
    
    context = {
        'sites': Site.objects.filter(is_active=True),
        'neighborhoods': Neighborhood.objects.filter(is_active=True).select_related('city'),
        'available_members': available_members,
    }
    
    return render(request, 'members/family_create.html', context)


@login_required
@role_required('admin', 'secretariat')
def family_edit(request, pk):
    """Modifier une famille."""
    family = get_object_or_404(Family, pk=pk)
    
    if request.method == 'POST':
        family.name = request.POST.get('name')
        family.site_id = request.POST.get('site') or None
        family.neighborhood_id = request.POST.get('neighborhood') or None
        family.address = request.POST.get('address', '')
        family.city = request.POST.get('city', '')
        family.postal_code = request.POST.get('postal_code', '')
        family.phone = request.POST.get('phone', '')
        family.email = request.POST.get('email', '')
        family.latitude = request.POST.get('latitude') or None
        family.longitude = request.POST.get('longitude') or None
        family.notes = request.POST.get('notes', '')
        family.save()
        
        messages.success(request, f"Famille '{family.name}' mise à jour.")
        return redirect('members:family_detail', pk=pk)
    
    context = {
        'family': family,
        'sites': Site.objects.filter(is_active=True),
        'neighborhoods': Neighborhood.objects.filter(is_active=True).select_related('city'),
    }
    
    return render(request, 'members/family_edit.html', context)


@login_required
@role_required('admin', 'secretariat')
def family_add_member(request, pk):
    """Ajouter à une famille : un membre existant, OU promouvoir un jeune / enfant du club
    en fiche Membre rattachée à la famille."""
    from apps.young.models import YoungMember
    from apps.bibleclub.models import Child

    family = get_object_or_404(Family, pk=pk)

    if request.method == 'POST':
        target_type = request.POST.get('target_type', 'member')
        family_role = request.POST.get('family_role', '') or Member.FamilyRole.CHILD

        if target_type == 'young':
            young_id = request.POST.get('young_id')
            young = get_object_or_404(YoungMember, pk=young_id)

            if young.linked_member:
                member = young.linked_member
            else:
                member = Member.objects.create(
                    first_name=young.first_name,
                    last_name=young.last_name,
                    date_of_birth=young.date_of_birth,
                    gender=young.gender or '',
                    email=young.email or '',
                    phone=young.phone or '',
                    address=young.address or '',
                    city=young.city or '',
                    postal_code=young.postal_code or '',
                    site=young.site,
                    status=Member.Status.ACTIF,
                )
                young.linked_member = member

            member.family = family
            member.family_role = family_role
            member.save()

            young.family = family
            young.save(update_fields=['family', 'linked_member'])

            messages.success(
                request,
                f"{young.first_name} {young.last_name} (jeunesse) ajouté(e) comme membre de la famille {family.name}.",
            )

        elif target_type == 'child':
            child_id = request.POST.get('child_id')
            child = get_object_or_404(Child, pk=child_id)

            if child.linked_member:
                member = child.linked_member
            else:
                member = Member.objects.create(
                    first_name=child.first_name,
                    last_name=child.last_name,
                    date_of_birth=child.date_of_birth,
                    gender=child.gender or '',
                    status=Member.Status.ACTIF,
                )
                child.linked_member = member

            member.family = family
            member.family_role = family_role
            member.save()

            child.family = family
            child.save(update_fields=['family', 'linked_member'])

            messages.success(
                request,
                f"{child.first_name} {child.last_name} (club biblique) ajouté(e) comme membre de la famille {family.name}.",
            )

        else:
            member_id = request.POST.get('member_id')
            member = get_object_or_404(Member, pk=member_id)
            member.family = family
            if family_role:
                member.family_role = family_role
            member.save()
            messages.success(
                request,
                f"{member.full_name} ajouté à la famille {family.name}.",
            )

        return redirect('members:family_detail', pk=pk)

    # Listes disponibles (sans famille et sans fiche membre liée déjà rattachée)
    available_members = Member.objects.filter(
        family__isnull=True,
        status='actif',
    ).order_by('last_name', 'first_name')

    available_young = YoungMember.objects.filter(
        is_active=True,
    ).filter(
        Q(linked_member__isnull=True) | Q(linked_member__family__isnull=True)
    ).order_by('last_name', 'first_name').distinct()

    available_children = Child.objects.filter(
        is_active=True,
    ).filter(
        Q(linked_member__isnull=True) | Q(linked_member__family__isnull=True)
    ).order_by('last_name', 'first_name').distinct()

    context = {
        'family': family,
        'available_members': available_members,
        'available_young': available_young,
        'available_children': available_children,
        'family_roles': [
            ('HEAD', 'Chef de famille'),
            ('SPOUSE', 'Conjoint(e)'),
            ('CHILD', 'Enfant'),
            ('PARENT', 'Parent'),
            ('OTHER', 'Autre'),
        ],
    }

    return render(request, 'members/family_add_member.html', context)
