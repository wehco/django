import unittest
try:
    set
except NameError:
    from sets import Set as set

from django.db import DatabaseError, connection
from django.db.models import Count
from django.test import TestCase

from models import Tag, Annotation, DumbCategory

class QuerysetOrderedTests(unittest.TestCase):
    """
    Tests for the Queryset.ordered attribute.
    """

    def test_no_default_or_explicit_ordering(self):
        self.assertEqual(Annotation.objects.all().ordered, False)

    def test_cleared_default_ordering(self):
        self.assertEqual(Tag.objects.all().ordered, True)
        self.assertEqual(Tag.objects.all().order_by().ordered, False)

    def test_explicit_ordering(self):
        self.assertEqual(Annotation.objects.all().order_by('id').ordered, True)

    def test_order_by_extra(self):
        self.assertEqual(Annotation.objects.all().extra(order_by=['id']).ordered, True)

    def test_annotated_ordering(self):
        qs = Annotation.objects.annotate(num_notes=Count('notes'))
        self.assertEqual(qs.ordered, False)
        self.assertEqual(qs.order_by('num_notes').ordered, True)


class SubqueryTests(TestCase):
    def setUp(self):
        DumbCategory.objects.create(id=1)
        DumbCategory.objects.create(id=2)
        DumbCategory.objects.create(id=3)

    def test_ordered_subselect(self):
        "Subselects honor any manual ordering"
        try:
            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:2])
            self.assertEquals(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[:2])
            self.assertEquals(set(query.values_list('id', flat=True)), set([2,3]))

            query = DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[2:])
            self.assertEquals(set(query.values_list('id', flat=True)), set([1]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connection.features.allow_sliced_subqueries)

    def test_sliced_delete(self):
        "Delete queries can safely contain sliced subqueries"
        try:
            DumbCategory.objects.filter(id__in=DumbCategory.objects.order_by('-id')[0:1]).delete()
            self.assertEquals(set(DumbCategory.objects.values_list('id', flat=True)), set([1,2]))
        except DatabaseError:
            # Oracle and MySQL both have problems with sliced subselects.
            # This prevents us from even evaluating this test case at all.
            # Refs #10099
            self.assertFalse(connection.features.allow_sliced_subqueries)
