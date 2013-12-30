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
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = u'Setup the domain for the default site.'
    
    def handle(self, *args, **kwargs):
        if len(args) != 1:
            raise CommandError("Usage setup_current_site <domain>")
        current_site = Site.objects.get_current()
        current_site.domain = args[0]
        current_site.save()
