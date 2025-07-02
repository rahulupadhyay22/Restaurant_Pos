from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class CategoryForm(FlaskForm):
    """Form for category management."""
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=64)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Category')


class MenuItemForm(FlaskForm):
    """Form for menu item management."""
    name = StringField('Item Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    has_half_option = BooleanField('Has Half Option')
    half_price = FloatField('Half Price', validators=[DataRequired(), NumberRange(min=0)])
    full_price = FloatField('Full Price', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    is_available = BooleanField('Available', default=True)
    image_url = StringField('Image URL', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Item') 