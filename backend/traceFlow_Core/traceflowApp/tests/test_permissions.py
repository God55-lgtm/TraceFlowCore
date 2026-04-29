import pytest
from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from traceflowApp.permissions import IsAuditor, IsAdmin, IsAuditorOrAdmin, IsDeveloper


@pytest.mark.django_db
def test_is_auditor_permission_granted():
    """Prueba que IsAuditor permite acceso a usuarios del grupo auditor."""
    user = User.objects.create_user(username="auditor_user", password="pass")
    group = Group.objects.create(name="auditor")
    user.groups.add(group)

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsAuditor()
    assert permission.has_permission(request, None) is True


@pytest.mark.django_db
def test_is_auditor_permission_denied():
    """Prueba que IsAuditor deniega acceso a usuarios sin grupo auditor."""
    user = User.objects.create_user(username="normal_user", password="pass")

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsAuditor()
    assert permission.has_permission(request, None) is False


@pytest.mark.django_db
def test_is_admin_permission_granted():
    """Prueba que IsAdmin permite acceso a usuarios del grupo admin."""
    user = User.objects.create_user(username="admin_user", password="pass")
    group = Group.objects.create(name="admin")
    user.groups.add(group)

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsAdmin()
    assert permission.has_permission(request, None) is True


@pytest.mark.django_db
def test_is_admin_permission_denied():
    """Prueba que IsAdmin deniega acceso a usuarios sin grupo admin."""
    user = User.objects.create_user(username="normal_user", password="pass")

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsAdmin()
    assert permission.has_permission(request, None) is False


@pytest.mark.django_db
def test_is_auditor_or_admin_permission():
    """Prueba que IsAuditorOrAdmin permite acceso a usuarios en auditor O admin."""
    user = User.objects.create_user(username="mixed_user", password="pass")
    group = Group.objects.create(name="auditor")
    user.groups.add(group)

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsAuditorOrAdmin()
    assert permission.has_permission(request, None) is True


@pytest.mark.django_db
def test_is_developer_permission_granted():
    """Prueba que IsDeveloper permite acceso a usuarios del grupo developer."""
    user = User.objects.create_user(username="dev_user", password="pass")
    group = Group.objects.create(name="developer")
    user.groups.add(group)

    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsDeveloper()
    assert permission.has_permission(request, None) is True