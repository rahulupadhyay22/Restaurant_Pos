from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

 
class TableForm(FlaskForm):
    """Form for table management."""
    name = StringField('Table Name', validators=[DataRequired(), Length(min=2, max=64)])
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1, max=50)])
    submit = SubmitField('Save Table') 