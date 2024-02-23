RITM_P_ALL = np.zeros(600)
RITM_R_ALL = np.zeros(600)

aa_P_ALL = np.zeros(600)
aa_LP_ALL = np.zeros(600)
aa_R_ALL = np.zeros(600)
aa_BETA_ALL = np.zeros(600)
aa_BETAMA_ALL = np.zeros(600)
aa_BETAC_ALL = np.zeros(600)

bb_P_ALL = np.zeros(600)
bb_LP_ALL = np.zeros(600)
bb_R_ALL = np.zeros(600)
bb_BETA_ALL = np.zeros(600)
bb_BETAMA_ALL = np.zeros(600)
bb_BETAC_ALL = np.zeros(600)

cc_P_ALL = np.zeros(600)
cc_LP_ALL = np.zeros(600)
cc_R_ALL = np.zeros(600)
cc_BETA_ALL = np.zeros(600)
cc_BETAMA_ALL = np.zeros(600)
cc_BETAC_ALL = np.zeros(600)




with requests.Session() as session:
    session.headers.update(API_KEY)

    holding_position = False
    while get_tick(session) < 600 and not shutdown:
        # print("running")
        tt = get_tick(session)
        RITM_P_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "RITM"}).json()[0][
            "last"]
        if tt > 2:
            RITM_R_ALL[tt - 1] = RITM_P_ALL[tt - 1] / RITM_P_ALL[tt - 2]

    # ALPHA
    aa_LP_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "ALPHA"}).json()[0][
        "last"]
    # Check if mega order exist,
    # 1.	If mega order does not exist, pass
    # 2.	if mega order does exist, retrieve price as pp00, size as size00, filled as ff00
    # 2.1 If ff00 == 0, pass
    # 	  2.2 If ff00 > 0, aa_P_ALL[tt-1] = pp00, k
    if mega_order_exists("ALPHA", "asks"):
        pp00, size00, ff00, mega_order_id = retrieve_mega_order("ALPHA")
        if ff00 == 0:
            aa_P_ALL[tt - 1] = aa_LP_ALL[tt - 1]
        if ff00 > 0:
            aa_P_ALL[tt - 1] = pp00
    else:
        aa_P_ALL[tt - 1] = aa_LP_ALL[tt - 1]
    # print("aa_P_ALL: ", aa_P_ALL[tt - 1])

    if tt > 2:
        if np.isnan(aa_P_ALL[tt - 1]):
            pp00 = aa_LP_ALL[tt - 1]
        else:
            pp00 = aa_P_ALL[tt - 1]

        if np.isnan(aa_P_ALL[tt - 2]):
            pp11 = aa_LP_ALL[tt - 2]
        else:
            pp11 = aa_P_ALL[tt - 2]

        aa_R_ALL[tt - 1] = pp00 / pp11
        # print("aa_R_ALL: ", aa_R_ALL[tt - 1])

    if tt > Windows1:

        sr00 = aa_R_ALL[tt - Windows1:tt]
        mr00 = RITM_R_ALL[tt - Windows1:tt]

        tmp1 = np.isnan(sr00)
        tmp2 = np.isnan(mr00)
        # merge tmp1 and tmp2 union set
        tmp3 = np.logical_and(~tmp1, ~tmp2)

        sr11 = sr00[tmp3]
        mr11 = mr00[tmp3]

        aa_BETA_ALL[tt - 1] = np.cov(sr11, mr11)[0][1] / np.var(sr11)

        if tt > 2 * Windows1:
            aa_BETAMA_ALL[tt - 1] = aa_BETA_ALL[tt - Windows1:tt].mean()
            if abs(aa_BETA_ALL[tt - 1] - aa_BETAMA_ALL[tt - 1]) >= 0.2:
                aa_BETAC_ALL[tt - 1] = aa_BETA_ALL[tt - 2]
            if abs(aa_BETA_ALL[tt - 1] - aa_BETAMA_ALL[tt - 1]) < 0.2:
                aa_BETAC_ALL[tt - 1] = aa_BETA_ALL[tt - 1]
        else:
            aa_BETAC_ALL[tt - 1] = aa_BETA_ALL[tt - 1]
    # THETA
    bb_LP_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "THETA"}).json()[0][
        "last"]
    # Check if mega order exist,
    # 1.	If mega order does not exist, pass
    # 2.	if mega order does exist, retrieve price as pp00, size as size00, filled as ff00
    # 2.1 If ff00 == 0, pass
    # 	  2.2 If ff00 > 0, bb_P_ALL[tt-1] = pp00, k
    if mega_order_exists("THETA", "asks"):
        pp00, size00, ff00, mega_order_id = retrieve_mega_order("THETA")
        if ff00 == 0:
            bb_P_ALL[tt - 1] = bb_LP_ALL[tt - 1]
        if ff00 > 0:
            bb_P_ALL[tt - 1] = pp00
    else:
        bb_P_ALL[tt - 1] = bb_LP_ALL[tt - 1]
    # print("bb_P_ALL: ", bb_P_ALL[tt - 1])

    if tt > 2:
        if np.isnan(bb_P_ALL[tt - 1]):
            pp00 = bb_LP_ALL[tt - 1]
        else:
            pp00 = bb_P_ALL[tt - 1]

        if np.isnan(bb_P_ALL[tt - 2]):
            pp11 = bb_LP_ALL[tt - 2]
        else:
            pp11 = bb_P_ALL[tt - 2]

        bb_R_ALL[tt - 1] = pp00 / pp11
        # print("bb_R_ALL: ", bb_R_ALL[tt - 1])

    if tt > Windows1:

        sr00 = bb_R_ALL[tt - Windows1:tt]
        mr00 = RITM_R_ALL[tt - Windows1:tt]

        tmp1 = np.isnan(sr00)
        tmp2 = np.isnan(mr00)
        # merge tmp1 and tmp2 union set
        tmp3 = np.logical_and(~tmp1, ~tmp2)

        sr11 = sr00[tmp3]
        mr11 = mr00[tmp3]

        bb_BETA_ALL[tt - 1] = np.cov(sr11, mr11)[0][1] / np.var(sr11)

        if tt > 2 * Windows1:
            bb_BETAMA_ALL[tt - 1] = bb_BETA_ALL[tt - Windows1:tt].mean()
            if abs(bb_BETA_ALL[tt - 1] - bb_BETAMA_ALL[tt - 1]) >= 0.2:
                bb_BETAC_ALL[tt - 1] = bb_BETA_ALL[tt - 2]
            if abs(bb_BETA_ALL[tt - 1] - bb_BETAMA_ALL[tt - 1]) < 0.2:
                bb_BETAC_ALL[tt - 1] = bb_BETA_ALL[tt - 1]
        else:
            bb_BETAC_ALL[tt - 1] = bb_BETA_ALL[tt - 1]
    # GAMMA
    CC_LP_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "GAMMA"}).json()[0][
        "last"]
    # Check if mega order exist,
    # 1.	If mega order does not exist, pass
    # 2.	if mega order does exist, retrieve price as pp00, size as size00, filled as ff00
    # 2.1 If ff00 == 0, pass
    # 	  2.2 If ff00 > 0, CC_P_ALL[tt-1] = pp00, k
    if mega_order_exists("GAMMA", "asks"):
        pp00, size00, ff00, mega_order_id = retrieve_mega_order("GAMMA")
        if ff00 == 0:
            CC_P_ALL[tt - 1] = CC_LP_ALL[tt - 1]
        if ff00 > 0:
            CC_P_ALL[tt - 1] = pp00
    else:
        CC_P_ALL[tt - 1] = CC_LP_ALL[tt - 1]
    # print("CC_P_ALL: ", CC_P_ALL[tt - 1])

    if tt > 2:
        if np.isnan(CC_P_ALL[tt - 1]):
            pp00 = CC_LP_ALL[tt - 1]
        else:
            pp00 = CC_P_ALL[tt - 1]

        if np.isnan(CC_P_ALL[tt - 2]):
            pp11 = CC_LP_ALL[tt - 2]
        else:
            pp11 = CC_P_ALL[tt - 2]

        CC_R_ALL[tt - 1] = pp00 / pp11
        # print("CC_R_ALL: ", CC_R_ALL[tt - 1])

    if tt > Windows1:

        sr00 = CC_R_ALL[tt - Windows1:tt]
        mr00 = RITM_R_ALL[tt - Windows1:tt]

        tmp1 = np.isnan(sr00)
        tmp2 = np.isnan(mr00)
        # merge tmp1 and tmp2 union set
        tmp3 = np.logical_and(~tmp1, ~tmp2)

        sr11 = sr00[tmp3]
        mr11 = mr00[tmp3]

        CC_BETA_ALL[tt - 1] = np.cov(sr11, mr11)[0][1] / np.var(sr11)

        if tt > 2 * Windows1:
            CC_BETAMA_ALL[tt - 1] = CC_BETA_ALL[tt - Windows1:tt].mean()
            if abs(CC_BETA_ALL[tt - 1] - CC_BETAMA_ALL[tt - 1]) >= 0.2:
                CC_BETAC_ALL[tt - 1] = CC_BETA_ALL[tt - 2]
            if abs(CC_BETA_ALL[tt - 1] - CC_BETAMA_ALL[tt - 1]) < 0.2:
                CC_BETAC_ALL[tt - 1] = CC_BETA_ALL[tt - 1]
        else:
            CC_BETAC_ALL[tt - 1] = CC_BETA_ALL[tt - 1]