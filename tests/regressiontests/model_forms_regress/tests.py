from datetime import date

from django import db
from django import forms
from django.forms.models import modelform_factory, ModelChoiceField
from django.conf import settings
from django.test import TestCase

from models import Person, Triple, FilePathModel, Article, Publication, CustomFF

class ModelMultipleChoiceFieldTests(TestCase):

    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True

    def tearDown(self):
        settings.DEBUG = self.old_debug

    def test_model_multiple_choice_number_of_queries(self):
        """
        Test that ModelMultipleChoiceField does O(1) queries instead of
        O(n) (#10156).
        """
        for i in range(30):
            Person.objects.create(name="Person %s" % i)

        db.reset_queries()
        f = forms.ModelMultipleChoiceField(queryset=Person.objects.all())
        selected = f.clean([1, 3, 5, 7, 9])
        self.assertEquals(len(db.connection.queries), 1)

class TripleForm(forms.ModelForm):
    class Meta:
        model = Triple

class UniqueTogetherTests(TestCase):
    def test_multiple_field_unique_together(self):
        """
        When the same field is involved in multiple unique_together
        constraints, we need to make sure we don't remove the data for it
        before doing all the validation checking (not just failing after
        the first one).
        """
        Triple.objects.create(left=1, middle=2, right=3)

        form = TripleForm({'left': '1', 'middle': '2', 'right': '3'})
        self.failIf(form.is_valid())

        form = TripleForm({'left': '1', 'middle': '3', 'right': '1'})
        self.failUnless(form.is_valid())

class FPForm(forms.ModelForm):
    class Meta:
        model = FilePathModel

class FilePathFieldTests(TestCase):
    def test_file_path_field_blank(self):
        """
        Regression test for #8842: FilePathField(blank=True)
        """
        form = FPForm()
        names = [p[1] for p in form['path'].field.choices]
        names.sort()
        self.assertEqual(names, ['---------', '__init__.py', 'models.py', 'tests.py'])

class ManyToManyCallableInitialTests(TestCase):
    def test_callable(self):
        "Regression for #10349: A callable can be provided as the initial value for an m2m field"

        # Set up a callable initial value
        def formfield_for_dbfield(db_field, **kwargs):
            if db_field.name == 'publications':
                kwargs['initial'] = lambda: Publication.objects.all().order_by('date_published')[:2]
            return db_field.formfield(**kwargs)

        # Set up some Publications to use as data
        Publication(title="First Book", date_published=date(2007,1,1)).save()
        Publication(title="Second Book", date_published=date(2008,1,1)).save()
        Publication(title="Third Book", date_published=date(2009,1,1)).save()

        # Create a ModelForm, instantiate it, and check that the output is as expected
        ModelForm = modelform_factory(Article, formfield_callback=formfield_for_dbfield)
        form = ModelForm()
        self.assertEquals(form.as_ul(), u"""<li><label for="id_headline">Headline:</label> <input id="id_headline" type="text" name="headline" maxlength="100" /></li>
<li><label for="id_publications">Publications:</label> <select multiple="multiple" name="publications" id="id_publications">
<option value="1" selected="selected">First Book</option>
<option value="2" selected="selected">Second Book</option>
<option value="3">Third Book</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>""")

class CFFForm(forms.ModelForm):
    class Meta:
        model = CustomFF

class CustomFieldSaveTests(TestCase):
    def test_save(self):
        "Regression for #11149: save_form_data should be called only once"
        
        # It's enough that the form saves without error -- the custom save routine will
        # generate an AssertionError if it is called more than once during save.
        form = CFFForm(data = {'f': None})
        form.save()

class ModelClassTests(TestCase):
    def test_no_model_class(self):
        class NoModelModelForm(forms.ModelForm):
            pass
        self.assertRaises(ValueError, NoModelModelForm)


class ModelChoiceForm(forms.Form):
    person = ModelChoiceField(Person.objects.all())


class TestTicket11183(TestCase):
    def test_11183(self):
        form1 = ModelChoiceForm()
        field1 = form1.fields['person']
        # To allow the widget to change the queryset of field1.widget.choices correctly, 
        # without affecting other forms, the following must hold:
        self.assert_(field1 is not ModelChoiceForm.base_fields['person'])
        self.assert_(field1.widget.choices.field is field1)
