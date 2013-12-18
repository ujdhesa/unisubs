# Amara, universalsubtitles.org
# 
# Copyright (C) 2013 Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see 
# http://www.gnu.org/licenses/agpl-3.0.html.

from django.core.management.base import BaseCommand, CommandError
from django.db.models.loading import get_model

class Command(BaseCommand):
    args = '<app name> <model_name> <field_name>'
    help = u'Recreate thumbnails'
    CHUNK_SIZE =25 # max number of objects to select at once
    
    def handle(self, *args, **kwargs):
        if len(args) != 3:
            raise CommandError("Usage: recreate_thumbs <app name> "
                               "<model_name> field_name>")
        Model = get_model(args[0], args[1])
        field_name = args[2]

        last_id = None
        while True:
            qs = Model.objects.filter(**{
                "%s__isnull" % field_name: False,
            }).order_by('id')
            if last_id is not None:
                qs = qs.filter(id__gt=last_id)

            found_obj = False
            for obj in qs[:self.CHUNK_SIZE]:
                found_obj = True
                last_id = obj.id
                try:
                    getattr(obj, field_name).recreate_all_thumbnails()
                except StandardError, e:
                    self.stdout.write("Error recreating thumbnails for "
                                      "%s: %s\n" % (obj, e))
                else:
                    self.stdout.write("Recreated thumbnails for %s\n" % (obj,))
            if not found_obj:
                break
