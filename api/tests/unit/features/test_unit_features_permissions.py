from unittest import TestCase, mock
from unittest.mock import MagicMock

import pytest

from features.models import Feature
from features.permissions import FeaturePermissions
from organisations.models import Organisation, OrganisationRole
from permissions.models import PermissionModel
from projects.models import (
    Project,
    UserPermissionGroupProjectPermission,
    UserProjectPermission,
)
from projects.permissions import (
    CREATE_FEATURE,
    DELETE_FEATURE,
    VIEW_PROJECT,
    NestedProjectPermissions,
)
from users.models import FFAdminUser, UserPermissionGroup

mock_view = mock.MagicMock()
mock_request = mock.MagicMock()

feature_permissions = FeaturePermissions()


@pytest.mark.django_db
class FeaturePermissionsTestCase(TestCase):
    def setUp(self) -> None:
        self.organisation = Organisation.objects.create(name="Test")
        self.project = Project.objects.create(
            name="Test project", organisation=self.organisation
        )

        self.feature = Feature.objects.create(name="Test feature", project=self.project)

        self.user = FFAdminUser.objects.create(email="user@test.com")
        self.user.add_organisation(self.organisation, OrganisationRole.USER)

        self.org_admin = FFAdminUser.objects.create(email="admin@test.com")
        self.org_admin.add_organisation(self.organisation, OrganisationRole.ADMIN)

        self.group = UserPermissionGroup.objects.create(
            name="Test group", organisation=self.organisation
        )
        self.group.users.add(self.user)

        mock_view.kwargs = {}
        mock_request.data = {}

    def test_organisation_admin_can_list_features(self):
        # Given
        mock_view.action = "list"
        mock_view.detail = False
        mock_view.kwargs["project_pk"] = self.project.id
        mock_request.user = self.org_admin

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert result

    def test_project_admin_can_list_features(self):
        # Given
        UserProjectPermission.objects.create(
            user=self.user, admin=True, project=self.project
        )

        mock_view.action = "list"
        mock_view.detail = False
        mock_view.kwargs["project_pk"] = self.project.id
        mock_request.user = self.user

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert result

    def test_project_user_with_read_access_can_list_features(self):
        # Given
        user_project_permission = UserProjectPermission.objects.create(
            user=self.user, admin=False, project=self.project
        )
        user_project_permission.set_permissions([VIEW_PROJECT])

        mock_view.action = "list"
        mock_view.detail = False
        mock_view.kwargs["project_pk"] = self.project.id
        mock_request.user = self.user

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert result

    def test_user_with_no_project_permissions_cannot_list_features(self):
        # Given
        mock_view.action = "list"
        mock_view.detail = False
        mock_view.kwargs["project_pk"] = self.project.id
        mock_request.user = self.user

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert not result

    def test_organisation_admin_can_create_feature(self):
        # Given
        mock_view.action = "create"
        mock_view.detail = False
        mock_request.user = self.org_admin
        mock_request.data = {"project": self.project.id, "name": "new feature"}

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert result

    def test_project_admin_can_create_feature(self):
        # Given
        # use a group to test groups work too
        UserPermissionGroupProjectPermission.objects.create(
            group=self.group, project=self.project, admin=True
        )
        mock_view.action = "create"
        mock_view.detail = False
        mock_request.user = self.user
        mock_request.data = {"project": self.project.id, "name": "new feature"}

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert result

    def test_project_user_with_create_feature_permission_can_create_feature(self):
        # Given
        # use a group to test groups work too
        user_group_permission = UserPermissionGroupProjectPermission.objects.create(
            group=self.group, project=self.project, admin=False
        )
        user_group_permission.add_permission(CREATE_FEATURE)
        mock_view.action = "create"
        mock_view.detail = False
        mock_request.user = self.user
        mock_request.data = {"project": self.project.id, "name": "new feature"}

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert result

    def test_project_user_without_create_feature_permission_cannot_create_feature(self):
        # Given
        mock_view.action = "create"
        mock_view.detail = False
        mock_request.user = self.user
        mock_request.data = {"project": self.project.id, "name": "new feature"}

        # When
        result = feature_permissions.has_permission(mock_request, mock_view)

        # Then
        assert not result

    def test_organisation_admin_can_view_feature(self):
        # Given
        mock_view.action = "retrieve"
        mock_view.detail = True
        mock_request.user = self.org_admin

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_admin_can_view_feature(self):
        # Given
        UserProjectPermission.objects.create(
            user=self.user, project=self.project, admin=True
        )
        mock_request.user = self.user
        mock_view.action = "retrieve"
        mock_view.detail = True

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_user_with_view_project_permission_can_view_feature(self):
        # Given
        user_permission = UserProjectPermission.objects.create(
            user=self.user, project=self.project, admin=False
        )
        user_permission.set_permissions([VIEW_PROJECT])
        mock_request.user = self.user
        mock_view.action = "retrieve"
        mock_view.detail = True

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_user_without_view_project_permission_cannot_view_feature(self):
        # Given
        mock_request.user = self.user
        mock_view.action = "retrieve"
        mock_view.detail = True

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert not result

    def test_organisation_admin_can_edit_feature(self):
        # Given
        mock_view.action = "update"
        mock_view.detail = True
        mock_request.user = self.org_admin

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_admin_can_edit_feature(self):
        # Given
        UserProjectPermission.objects.create(
            user=self.user, project=self.project, admin=True
        )
        mock_view.action = "update"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_user_cannot_edit_feature(self):
        # Given
        mock_view.action = "update"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert not result

    def test_organisation_admin_can_delete_feature(self):
        # Given
        mock_view.action = "destroy"
        mock_view.detail = True
        mock_request.user = self.org_admin

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_admin_can_delete_feature(self):
        # Given
        UserProjectPermission.objects.create(
            user=self.user, project=self.project, admin=True
        )
        mock_view.action = "destroy"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_user_with_delete_feature_permission_can_delete_feature(self):
        # Given
        user_project_permission = UserProjectPermission.objects.create(
            user=self.user, project=self.project
        )
        user_project_permission.add_permission(DELETE_FEATURE)

        mock_view.action = "destroy"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_user_without_delete_feature_permission_cannot_delete_feature(self):
        # Given
        mock_view.action = "destroy"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert not result

    def test_organisation_admin_can_update_feature_segments(self):
        # Given
        mock_view.action = "segments"
        mock_view.detail = True
        mock_request.user = self.org_admin

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_admin_can_update_feature_segments(self):
        # Given
        UserProjectPermission.objects.create(
            user=self.user, project=self.project, admin=True
        )
        mock_view.action = "segments"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert result

    def test_project_user_cannot_update_feature_segments(self):
        # Given
        mock_view.action = "segments"
        mock_view.detail = True
        mock_request.user = self.user

        # When
        result = feature_permissions.has_object_permission(
            mock_request, mock_view, self.feature
        )

        # Then
        assert not result


@pytest.mark.parametrize(
    "action_permission_map, action, user_permission, expected_result",
    (
        ({}, "list", None, False),
        ({}, "list", VIEW_PROJECT, True),
        ({"create": CREATE_FEATURE}, "create", None, False),
        ({"create": CREATE_FEATURE}, "create", CREATE_FEATURE, True),
    ),
)
def test_nested_project_permissions_has_permission(
    action_permission_map,
    action,
    user_permission,
    expected_result,
    project,
    django_user_model,
):
    # Given
    user = django_user_model.objects.create(email="test@example.com")
    user.add_organisation(project.organisation)

    if user_permission:
        permission_model = PermissionModel.objects.get(key=user_permission)
        user_project_permission = UserProjectPermission.objects.create(
            user=user, project=project, admin=False
        )
        user_project_permission.permissions.add(permission_model)

    permission_class = NestedProjectPermissions(
        action_permission_map=action_permission_map
    )

    request = MagicMock(user=user)
    view = MagicMock(action=action, kwargs={"project_pk": project.id})

    # When
    result = permission_class.has_permission(request, view)

    # Then
    assert result == expected_result


@pytest.mark.parametrize(
    "action_permission_map, action, user_permission, expected_result",
    (
        ({}, "list", None, False),
        ({}, "list", VIEW_PROJECT, True),
        ({"update": CREATE_FEATURE}, "update", None, False),
        ({"update": CREATE_FEATURE}, "update", CREATE_FEATURE, True),
    ),
)
def test_nested_project_permissions_has_object_permission(
    action_permission_map,
    action,
    user_permission,
    expected_result,
    project,
    django_user_model,
):
    # Given
    user = django_user_model.objects.create(email="test@example.com")
    user.add_organisation(project.organisation)

    if user_permission:
        permission_model = PermissionModel.objects.get(key=user_permission)
        user_project_permission = UserProjectPermission.objects.create(
            user=user, project=project, admin=False
        )
        user_project_permission.permissions.add(permission_model)

    permission_class = NestedProjectPermissions(
        action_permission_map=action_permission_map
    )

    request = MagicMock(user=user)
    view = MagicMock(action=action, kwargs={"project_pk": project.id})

    obj = MagicMock(project=project)

    # When
    result = permission_class.has_object_permission(request, view, obj)

    # Then
    assert result == expected_result
