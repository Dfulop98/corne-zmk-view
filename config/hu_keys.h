/*
 * Hungarian (QWERTZ) OS layout -> ZMK keycodes.
 * The OS is set to Hungarian, so the firmware must send the US keycode
 * that produces the wanted character on the HU layout.
 */
#pragma once

/* Letters swapped on QWERTZ */
#define HU_Z      &kp Y
#define HU_Y      &kp Z

/* Accented letters */
#define HU_OE     &kp N0            /* ö */
#define HU_UE     &kp MINUS         /* ü */
#define HU_OA     &kp EQUAL         /* ó */
#define HU_OEE    &kp LBKT          /* ő */
#define HU_UA     &kp RBKT          /* ú */
#define HU_EA     &kp SEMI          /* é */
#define HU_AA     &kp SQT           /* á */
#define HU_UEE    &kp NON_US_HASH   /* ű */
#define HU_IA     &kp NON_US_BSLH   /* í */

/* Digits (0 is left of 1 on HU) */
#define HU_0      &kp GRAVE

/* Shift + number row */
#define HU_SQT    &kp LS(N1)        /* ' */
#define HU_DQT    &kp LS(N2)        /* " */
#define HU_PLUS   &kp LS(N3)        /* + */
#define HU_EXCL   &kp LS(N4)        /* ! */
#define HU_PRCT   &kp LS(N5)        /* % */
#define HU_SLSH   &kp LS(N6)        /* / */
#define HU_EQL    &kp LS(N7)        /* = */
#define HU_LPAR   &kp LS(N8)        /* ( */
#define HU_RPAR   &kp LS(N9)        /* ) */

/* Punctuation on the base layer */
#define HU_MINUS  &kp FSLH          /* - */
#define HU_UNDER  &kp LS(FSLH)      /* _ */
#define HU_QUES   &kp LS(COMMA)     /* ? */
#define HU_COLON  &kp LS(DOT)       /* : */

/* AltGr symbols: &ag = AltGr macro in corne.keymap (Remote Desktop safe) */
#define HU_BSLH   &ag Q             /* \ */
#define HU_PIPE   &ag W             /* | */
#define HU_AT     &ag V             /* @ */
#define HU_HASH   &ag X             /* # */
#define HU_DLR    &ag SEMI          /* $ */
#define HU_AMPS   &ag C             /* & */
#define HU_STAR   &ag FSLH          /* * */
#define HU_SEMI   &ag COMMA         /* ; */
#define HU_LT     &ag NON_US_BSLH     /* < */
#define HU_GT     &ag Z             /* > */
#define HU_LBKT   &ag F             /* [ */
#define HU_RBKT   &ag G             /* ] */
#define HU_LBRC   &ag B             /* { */
#define HU_RBRC   &ag N             /* } */
#define HU_TILDE  &ag N1            /* ~ (not a dead key on Windows HU) */
#define HU_GRAVE  &ag N7            /* ` (not a dead key on Windows HU) */
/* ^ is AltGr+3 but a dead key on Windows HU -> use the &hu_caret macro */

/* Clipboard (Ctrl+Z is Ctrl + US-Y on QWERTZ) */
#define HU_UNDO   &kp LC(Y)
#define HU_REDO   &kp LC(Z)
#define HU_CUT    &kp LC(X)
#define HU_COPY   &kp LC(C)
#define HU_PASTE  &kp LC(V)
