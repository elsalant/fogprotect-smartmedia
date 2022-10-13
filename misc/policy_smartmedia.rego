    package dataapi.authz

   rule[{"name": "Block specific user", "action": "BlockUser"}] {
      input.request.method == "GET"
      input.request.situationStatus == "unsafe-user"
      lower(input.request.user) == lower(input.request.unsafeUserName)
    }

   rule[{"name": "Block specific role", "action": "BlockRole"}] {
      input.request.method == "GET"
      input.request.situationStatus == "unsafe-role"
      lower(input.request.role) == lower(input.request.unsafeRoleName)
    }

    rule[{"name": "Only allow administrator GET access to assets when organization is unsafe and not VRT(1)", "action": "BlockResource"}]{
      input.request.situationStatus == "organization-unsafe"
      input.request.method == "GET"
      lower(input.request.organization) != lower("VRT")
    }

    rule[{"name": "Only allow administrator GET access to assets when organization is unsafe and not VRT(2)", "action": "BlockResource"}]{
      input.request.situationStatus == "organization-unsafe"
      input.request.method == "GET"
      lower(input.request.organization) == lower("VRT")
      lower(input.request.role) != lower("Admin")
    }

    rule[{"name": "Block video-booth_operator from GETting videos", "action": "BlockResource"}]{
      input.request.method == "GET"
      lower(input.request.role) == lower("video-booth-operator")
      input.request.asset.name == "videos"
    }
    
    rule[{"name": "Block video-editor from POSTting", "action": "BlockResource"}]{
      input.request.method == "POST"
      lower(input.request.role) == lower("video-editor")
    }
    
    rule[{"name": "Block video-editor from GETting surveys", "action": "BlockResource"}]{
      input.request.method == "GET"
      lower(input.request.role) == lower("video-editor")
      contains(input.request.asset.name, "survey")
    }

    rule[{"name": "Block video-editor from GETting videos if video editor is unsafe", "action": "BlockResource"}]{
      input.request.method == "GET"
      lower(input.request.role) == lower("video-booth-editor")
      input.request.asset.name == "videos"
      input.request.situationStatus == "video-editor-unsafe"
    }
    
    rule[{"name": "Block video-booth-operator from GETting surveys if video-booth-operator is unsafe", "action": "BlockResource"}]{
      input.request.method == "GET"
      lower(input.request.role) == lower("video-booth-operator")
      contains(input.request.asset.name, "survey")
      input.request.situationStatus == "video-booth-operator-unsafe"
    }
