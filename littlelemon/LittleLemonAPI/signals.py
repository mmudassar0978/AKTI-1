from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group
from django.dispatch import receiver

@receiver(post_migrate)
def create_groups(sender, **kwargs):
    # Create Manager group
    manager_group, created = Group.objects.get_or_create(name='Manager')
    
    # Create Delivery Crew group
    delivery_crew_group, created = Group.objects.get_or_create(name='Delivery Crew')